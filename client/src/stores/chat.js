import { defineStore } from "pinia";
import { topologyService } from "../services/api";

export const useChatStore = defineStore("chat", {
  state: () => ({
    sessions: [],
    currentSession: null,
    messages: [],
    loading: false,
    error: null,
    streaming: false,
    selectedModel: "qwen",
    selectedMode: "agent",
    sessionStarted: false,
  }),

  actions: {
    async fetchSessions(topologyId) {
      this.loading = true;
      this.error = null;
      try {
        const response = await topologyService.getChatSessions(topologyId);
        this.sessions = response.data;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async deleteSession(topologyId, sessionId) {
      this.loading = true;
      this.error = null;

      try {
        await topologyService.deleteChatSession(topologyId, sessionId);

        await this.fetchSessions(topologyId);
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async renameSession(topologyId, sessionId, newTitle) {
      this.loading = true;
      this.error = null;

      try {
        await topologyService.renameChatSession(
          topologyId,
          sessionId,
          newTitle
        );

        await this.fetchSessions(topologyId);
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async fetchHistory(topologyId, sessionId) {
      this.loading = true;
      this.error = null;
      try {
        const response = await topologyService.getChatHistory(
          topologyId,
          sessionId
        );
        this.messages = response.data;

        const session = this.sessions.find((s) => s.id === sessionId);
        if (session) {
          this.selectedModel = session.model || "qwen";
          this.selectedMode = session.mode || "ask";
          this.sessionStarted = true;
        }
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async sendMessage(topologyId, sessionId, content) {
      this.streaming = true;
      this.error = null;

      this.messages.push({
        role: "user",
        content,
        created_at: new Date().toISOString(),
      });

      try {
        const { response, sessionId: newSessionId } =
          await topologyService.sendMessage(
            topologyId,
            sessionId,
            content,
            this.selectedModel,
            this.selectedMode
          );

        if (sessionId === "new" && newSessionId) {
          this.currentSession = newSessionId;
          this.sessionStarted = true;
        } else if (sessionId !== "new") {
          this.sessionStarted = true;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        const assistantMessageIndex = this.messages.length;
        this.messages.push({
          role: "assistant",
          content: "",
          created_at: new Date().toISOString(),
        });

        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");

          // Keep the last incomplete line in the buffer
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.trim()) continue;

            if (line.startsWith("data: ")) {
              const jsonStr = line.substring(6); // Remove "data: "

              try {
                const payload = JSON.parse(jsonStr);

                // Handle Error
                if (payload.error) {
                  this.error = payload.error;
                  // Optional: Stop streaming if error occurs
                  return newSessionId || sessionId;
                }

                // Handle Text Content
                if (payload.text) {
                  this.messages[assistantMessageIndex].content += payload.text;
                }
              } catch (e) {
                console.error("Failed to parse SSE JSON:", e);
              }
            }
          }
        }

        return newSessionId || sessionId;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.streaming = false;
      }
    },

    setCurrentSession(session) {
      this.currentSession = session;
      this.sessionStarted = session !== null && session !== "new";
    },

    clearMessages() {
      this.messages = [];
      this.sessionStarted = false;
    },

    setModel(model) {
      if (!this.sessionStarted) {
        this.selectedModel = model;
      }
    },

    setMode(mode) {
      if (!this.sessionStarted) {
        this.selectedMode = mode;
      }
    },

    resetSession() {
      this.currentSession = null;
      this.messages = [];
      this.sessionStarted = false;
    },

    async stopAgent(topologyId) {
      if (!this.currentSession || this.selectedMode !== "agent") {
        return;
      }

      try {
        await topologyService.stopAgentChat(topologyId, this.currentSession);
        this.streaming = false;
      } catch (error) {
        this.error = error.message;
        throw error;
      }
    },
  },
});
