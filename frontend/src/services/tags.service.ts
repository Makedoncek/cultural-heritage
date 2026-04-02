import api from './api'
import type {Tag, PaginatedResponse} from '../types'

export const tagsService = {
    getAll: (tagType?: string) =>
        api.get<PaginatedResponse<Tag>>('/tags/', {params: tagType ? {tag_type: tagType} : {}}).then(res => res.data),
}
