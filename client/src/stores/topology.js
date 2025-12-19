import { defineStore } from "pinia";
import { topologyService } from "../services/api";

export const useTopologyStore = defineStore("topology", {
  state: () => ({
    topologies: [],
    currentTopology: null,
    devices: [],
    loading: false,
    error: null,
    currentTask: null,
  }),

  actions: {
    async fetchTopologies() {
      this.loading = true;
      this.error = null;
      try {
        const response = await topologyService.getAll();
        this.topologies = response.data;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async fetchTopologyDetail(topologyId) {
      this.loading = true;
      this.error = null;

      try {
        const response = await topologyService.get(topologyId);

        // Backend returns a single object, not an array
        this.currentTopology = response.data;

        this.fetchDevices(topologyId);
      } catch (error) {
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },

    async fetchDevices(topologyId) {
      this.loading = true;
      this.error = null;
      try {
        const response = await topologyService.getDevices(topologyId);

        this.devices = response.data;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async updateUserCredentials(topologyId, credentials) {
      this.loading = true;
      this.error = null;
      try {
        const response = await topologyService.updateUser(
          topologyId,
          credentials
        );
        // Update current topology with new credentials
        if (this.currentTopology) {
          this.currentTopology = {
            ...this.currentTopology,
            username: credentials.username,
            password: credentials.password,
          };
        }
        return response.data;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async updateDeviceIp(topologyId, deviceId, ipAddress) {
      this.error = null;
      try {
        const response = await topologyService.updateDeviceIp(
          topologyId,
          deviceId,
          ipAddress
        );
        return response.data;
      } catch (error) {
        this.error = error.message;
        throw error;
      }
    },

    async refreshConfigs(topologyId) {
      this.error = null;
      try {
        const response = await topologyService.refreshConfigs(topologyId);
        const taskId = response.data.task_id;

        if (taskId) {
          this.currentTask = {
            id: taskId,
            status: "running",
            progress: 0,
            message: response.data.message,
          };

          this.pollTaskStatus(topologyId, taskId);
        }

        return response.data;
      } catch (error) {
        this.error = error.message;
        throw error;
      }
    },

    async pollTaskStatus(topologyId, taskId) {
      const poll = async () => {
        try {
          const response = await topologyService.getTaskStatus(
            topologyId,
            taskId
          );
          const task = response.data;

          this.currentTask = {
            id: taskId,
            status: task.status,
            progress: task.progress || 0,
            message: task.message || "Processing...",
            completed_devices: task.completed_devices || 0,
            total_devices: task.total_devices || 0,
          };

          if (task.status === "completed") {
            await this.fetchDevices(topologyId);
            setTimeout(() => {
              this.currentTask = null;
            }, 3000);
          } else if (task.status === "failed") {
            this.error = task.message;
            setTimeout(() => {
              this.currentTask = null;
            }, 5000);
          } else if (task.status === "running") {
            setTimeout(poll, 1000);
          }
        } catch (error) {
          console.error("Failed to poll task status:", error);
          this.error = "Task polling failed";
          this.currentTask = null;
        }
      };

      setTimeout(poll, 500);
    },

    setCurrentTopology(topology) {
      this.currentTopology = topology;
    },
  },
});
