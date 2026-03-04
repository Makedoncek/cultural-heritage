import api from './api'
import type {Tag, PaginatedResponse} from '../types'

export const tagsService = {
    getAll: () =>
        api.get<PaginatedResponse<Tag>>('/tags/').then(res => res.data),
}