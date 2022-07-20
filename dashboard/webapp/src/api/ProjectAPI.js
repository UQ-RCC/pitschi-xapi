import request from '@/utils/request'
import Vue from 'vue'

export default {
    // list all projects
    async getProjects() {
      const { data } = await request.get(`${Vue.prototype.$Config.backend}/api/projects`)
      return data
    },

    // sync
    async manualSync(){
      const { data } = await request.post(`${Vue.prototype.$Config.backend}/api/projects`)
      return data
    },

    // get single project
    async getProject(pid) {
      const { data } = await request.get(`${Vue.prototype.$Config.backend}/api/projects/${pid}`)
      return data
    }

}