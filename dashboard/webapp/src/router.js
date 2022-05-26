import Vue from 'vue'
import Router from 'vue-router'
import Home from './views/Home.vue'
import Projects from './views/Projects.vue'
import Collections from './views/Collections.vue'

Vue.use(Router)

export default new Router({
    mode: 'home',
    base: process.env.BASE_URL,
    routes: [
        {
            path: '/',
            name: 'home',
            component: Home
        },
        {
            path: '/projects',
            name: 'Projects',
            component: Projects
        },
        {
            path: '/collections',
            name: 'Collections',
            component: Collections
        },
        { path: '*', redirect: '/home' }  
    ]
})
