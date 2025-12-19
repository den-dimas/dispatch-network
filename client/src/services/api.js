import axios from "axios";

const api = axios.create({
  baseURL: "/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

export const topologyService = {
  getAll: () => api.get("/topologies/"),

  get: (topologyId) => api.get(`/topologies/${topologyId}`),

  create: (data) => api.post("/topologies/", data),

  updateUser: (topologyId, data) =>
    api.patch(`/topologies/${topologyId}`, data),

  getDevices: (topologyId) => api.get(`/topologies/${topologyId}/devices`),

  updateDeviceIp: (topologyId, deviceId, ipAddress) =>
    api.patch(`/topologies/${topologyId}/devices/${deviceId}`, { ip_address: ipAddress }),

  refreshConfigs: (topologyId) =>
    api.post(`/topologies/${topologyId}/config/refresh`),

  getTaskStatus: (topologyId, taskId) =>
    api.get(`/topologies/${topologyId}/task/${taskId}`),

  getChatSessions: (topologyId) => api.get(`/topologies/${topologyId}/chat`),

  deleteChatSession: (topologyId, sessionId) =>
    api.delete(`/topologies/${topologyId}/chat/${sessionId}`),

  renameChatSession: (topologyId, sessionId, title) =>
    api.put(`/topologies/${topologyId}/chat/${sessionId}`, { title }),

  getChatHistory: (topologyId, sessionId) =>
    api.get(`/topologies/${topologyId}/chat/${sessionId}/history`),

  sendMessage: async (
    topologyId,
    sessionId,
    content,
    model,
    mode = "agent"
  ) => {
    const endpoint = mode === "agent" ? "agent" : "ask";
    const response = await fetch(
      `/v1/topologies/${topologyId}/chat/${sessionId}/${endpoint}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ content, model }),
      }
    );

    return {
      response,
      sessionId: response.headers.get("X-Session-ID"),
    };
  },

  stopAgentChat: (topologyId, sessionId) =>
    api.post(`/topologies/${topologyId}/chat/${sessionId}/stop`),
};

export default api;
