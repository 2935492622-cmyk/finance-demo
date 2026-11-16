import { reactive } from 'vue'
import { filterParams, transactionPayload } from '../utils/filters.js'

export function createLedger(api) {
  const state = reactive({
    snapshot: null, loading: false, submitting: false, error: '',
    notice: null, fieldErrors: {}, lastSynced: null, uncertainWrite: false,
    filters: {}, editing: null, deleteTarget: null, deleteError: '',
  })
  let revision = 0
  let controller

  async function refresh(filters = state.filters) {
    const requestedFilters = filterParams(filters)
    state.filters = requestedFilters
    const current = ++revision
    controller?.abort()
    controller = new AbortController()
    state.loading = true
    state.error = ''
    try {
      const [records, summary] = await Promise.all([
        api.list({ signal: controller.signal, filters: requestedFilters }),
        api.summary({ signal: controller.signal, filters: requestedFilters }),
      ])
      if (current !== revision) return false
      // Commit a complete pair only. Never mix a new list with an older summary.
      state.snapshot = { records, summary, filters: requestedFilters }
      state.lastSynced = new Date()
      if (state.uncertainWrite) {
        state.notice = { tone: 'warning', message: '账本已重新同步，请核对明细，确认上一笔操作的结果后再决定是否重试。' }
        state.deleteTarget = null
        state.deleteError = ''
      }
      state.uncertainWrite = false
      return true
    } catch (error) {
      if (current !== revision || error.canceled) return false
      state.error = error.message || '账本同步失败，请重试。'
      return false
    } finally {
      if (current === revision) state.loading = false
    }
  }

  async function save(payload) {
    if (state.submitting || state.uncertainWrite) return false
    state.submitting = true
    state.notice = null
    state.fieldErrors = {}
    try {
      const editingId = state.editing?.id
      const record = editingId
        ? await api.update(editingId, transactionPayload(payload))
        : await api.create(transactionPayload(payload))
      state.editing = null
      const confirmedMessage = editingId ? '记录已更新。' : '已记下这一笔。'
      state.notice = { tone: 'success', message: confirmedMessage }
      const fresh = await refresh()
      if (!fresh) state.notice = { tone: 'warning', message: '记录已保存，但账本刷新失败。请重新同步，不要重复提交。' }
      else if (Object.keys(state.filters).length && !state.snapshot.records.items.some((item) => item.id === record.id)) {
        // Trust the refreshed database query, including its collation semantics.
        state.notice = { tone: 'success', message: `${confirmedMessage} 这笔记录不符合当前筛选，清空筛选后可查看。` }
      }
      return true
    } catch (error) {
      for (const detail of error.details || []) {
        if (detail.field.startsWith('body.')) state.fieldErrors[detail.field.slice(5)] = detail.message
      }
      state.uncertainWrite = Boolean(error.uncertain)
      state.notice = { tone: 'error', message: error.message || '保存失败，请重试。' }
      return false
    } finally { state.submitting = false }
  }

  function startEdit(record) {
    if (state.submitting || state.uncertainWrite) return false
    state.editing = { ...record }
    state.fieldErrors = {}
    return true
  }

  function cancelEdit() {
    if (state.submitting) return false
    state.editing = null
    state.fieldErrors = {}
    return true
  }

  function requestDelete(record) {
    if (state.submitting || state.uncertainWrite) return false
    state.deleteTarget = { ...record }
    state.deleteError = ''
    return true
  }

  function cancelDelete() {
    if (state.submitting) return false
    state.deleteTarget = null
    state.deleteError = ''
    return true
  }

  async function confirmDelete() {
    if (!state.deleteTarget || state.submitting || state.uncertainWrite) return false
    state.submitting = true
    state.deleteError = ''
    state.notice = null
    const id = state.deleteTarget.id
    try {
      await api.remove(id)
      state.deleteTarget = null
      if (state.editing?.id === id) cancelEditAfterDelete()
      state.notice = { tone: 'success', message: '记录已删除。' }
      if (!await refresh()) state.notice = { tone: 'warning', message: '记录已删除，但账本刷新失败。请重新同步。' }
      return true
    } catch (error) {
      state.uncertainWrite = Boolean(error.uncertain)
      state.deleteError = error.message || '删除失败，请稍后重试。'
      state.notice = { tone: 'error', message: state.deleteError }
      return false
    } finally { state.submitting = false }
  }

  function cancelEditAfterDelete() {
    state.editing = null
    state.fieldErrors = {}
  }

  function dispose() {
    revision += 1
    controller?.abort()
  }

  return { state, refresh, save, startEdit, cancelEdit, requestDelete, cancelDelete, confirmDelete, dispose }
}
