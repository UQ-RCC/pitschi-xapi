import request from '@/utils/request'
import Vue from 'vue'

export default {
    // get collections
    async getCollections() {
      const { data } = await request.get(`${Vue.prototype.$Config.backend}/api/collections`)
      return data
    },

      // get a collection
      async getCollection(collectionid) {
        const { data } = await request.get(`${Vue.prototype.$Config.backend}/api/collections/${collectionid}`)
        return data
      },

      // get collection caches
      async getCollectionCaches(collectionid) {
        const { data } = await request.get(`${Vue.prototype.$Config.backend}/api/collections/${collectionid}/caches`)
        return data
      },

      // get caches
      async getCaches() {
        const { data } = await request.get(`${Vue.prototype.$Config.backend}/api/caches`)
        return data
      },

      // create collection caches
      async createCollectionCache(collectionid, cache_name, priority) {
        let cacheinfo = {
                          "collection_name": collectionid,
                          "cache_name": cache_name,
                          "priority": priority
                        }
        const { data } = await request.put(`${Vue.prototype.$Config.backend}/api/collections/${collectionid}/caches`, cacheinfo)
        return data
      },

      // delete collection cache
      async deleteCollectionCache(collectionid, cache_name) {
        const { data } = await request.delete(`${Vue.prototype.$Config.backend}/api/collections/${collectionid}/caches/${cache_name}`)
        return data
      },
      
}