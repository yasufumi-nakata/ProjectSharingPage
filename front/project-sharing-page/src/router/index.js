import Vue from 'vue'
import VueRouter from 'vue-router'
import Home from '../views/Home.vue'
import Project from "../views/Project";
import Login from "../views/Login";
import User from "../views/User";
import Chat from "../views/Chat";

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/project/:projectId',
    name: 'Project',
    component: Project
  },
  {
    path: '/project/:projectId/:channel/:room',
    name: "Chat",
    component: Chat
  },
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/user/:userName',
    name: 'UserPage',
    component: User
  }
]

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes
})

export default router
