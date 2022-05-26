import request from '@/utils/request'
import Vue from 'vue'

export default {
    // check mounts
    async getProjects() {
      const { data } = await request.get(`${Vue.prototype.$Config.backend}/api/projects`)
      return data
    },

}