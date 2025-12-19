import { createRouter, createWebHistory } from 'vue-router';
import TopologyList from '../views/TopologyList.vue';
import TopologyDetail from '../views/TopologyDetail.vue';

const routes = [
  {
    path: '/',
    name: 'TopologyList',
    component: TopologyList
  },
  {
    path: '/topology/:id',
    name: 'TopologyDetail',
    component: TopologyDetail
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
