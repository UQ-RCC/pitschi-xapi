import Vue from 'vue'
import Router from 'vue-router'
import Home from './views/Home.vue'
import Projects from './views/Projects.vue'
import Collection from './views/Collection.vue'
import Project from './views/Project.vue'

Vue.use(Router)

export default new Router({
    mode: 'history',
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
            path: '/project',
            name: 'Project',
            component: Project
        },
        {
            path: '/collection',
            name: 'Collection',
            component: Collection
        },
        { path: '*', redirect: '/home' }  
    ]
})
