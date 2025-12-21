<template>
    <Dialog :open="true" @update:open="$emit('close')">
        <DialogContent class="sm:max-w-175 max-h-[80vh] flex flex-col">
            <DialogHeader>
                <DialogTitle>Devices</DialogTitle>
                <DialogDescription>
                    List of devices in this topology with their configurations.
                </DialogDescription>
            </DialogHeader>

            <div class="flex-1 overflow-y-auto py-4">
                <div v-if="loading" class="flex justify-center py-8">
                    <Loader2 class="h-6 w-6 animate-spin text-primary" />
                </div>

                <div v-else-if="devices.length === 0" class="text-center py-8 text-muted-foreground">
                    <p>No devices found</p>
                </div>

                <div v-else class="space-y-3">
                    <div v-for="device in devices" :key="device.device_id" class="bg-muted/50 border rounded-lg p-4">
                        <div class="flex justify-between items-start gap-4">
                            <div class="flex-1">
                                <div class="flex items-center gap-2 mb-2">
                                    <h4 class="font-semibold">{{ device.name }}</h4>
                                    <CheckCircle2 v-if="device.has_config" class="h-4 w-4 text-green-600"
                                        title="Config snapshot exists" />
                                </div>

                                <div class="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                                    <span>Type: {{ device.device_type || 'Unknown' }}</span>
                                    <span v-if="device.port">• Port: {{ device.port }}</span>
                                </div>

                                <div v-if="device.device_type === 'Router'" class="flex items-center gap-2 mb-2">
                                    <Input v-if="editingDevice === device.device_id" v-model="editingIp"
                                        placeholder="192.168.1.1" class="h-8 text-sm"
                                        @keyup.enter="saveDeviceIp(device)" @keyup.escape="cancelEdit" />
                                    <span v-else class="text-sm">
                                        IP: {{ device.ip_address || 'Not set' }}
                                    </span>

                                    <Button v-if="editingDevice === device.device_id" variant="ghost" size="icon"
                                        class="h-6 w-6" @click="saveDeviceIp(device)" :disabled="savingIp">
                                        <Loader2 v-if="savingIp" class="h-3 w-3 animate-spin" />
                                        <Check v-else class="h-3 w-3" />
                                    </Button>
                                    <Button v-if="editingDevice === device.device_id" variant="ghost" size="icon"
                                        class="h-6 w-6" @click="cancelEdit">
                                        <X class="h-3 w-3" />
                                    </Button>
                                    <Button v-else variant="ghost" size="icon" class="h-6 w-6"
                                        @click="startEditIp(device)">
                                        <Pencil class="h-3 w-3" />
                                    </Button>
                                </div>

                                <div v-if="device.latest_config" class="mt-3">
                                    <Button variant="outline" size="sm" @click="openConfigModal(device)"
                                        class="w-full justify-between">
                                        <span class="text-xs">View Config</span>
                                        <ChevronRight class="h-3 w-3" />
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </DialogContent>
    </Dialog>

    <!-- Config View Modal -->
    <Dialog :open="!!viewingConfigDevice" @update:open="closeConfigModal">
        <DialogContent class="sm:max-w-3xl max-h-[80vh] flex flex-col">
            <DialogHeader>
                <DialogTitle class="flex items-center gap-2">
                    <FileText class="h-5 w-5 text-primary" />
                    <span>Configuration: {{ viewingConfigDevice?.name }}</span>
                </DialogTitle>
                <DialogDescription>
                    Last updated: {{ formatDate(viewingConfigDevice?.config_updated_at) }}
                </DialogDescription>
            </DialogHeader>

            <div class="flex-1 min-h-0 bg-muted/50 rounded-md border mt-2 relative group flex flex-col">
                <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                    <Button variant="secondary" size="sm" class="h-8 text-xs" @click="copyConfig">
                        <Copy class="h-3 w-3 mr-1" />
                        Copy
                    </Button>
                </div>
                <div class="flex-1 overflow-auto p-4 w-full">
                    <pre
                        class="text-xs font-mono whitespace-pre-wrap break-all text-foreground">{{ viewingConfigDevice?.latest_config }}</pre>
                </div>
            </div>
        </DialogContent>
    </Dialog>
</template>

<script setup>
import { ref } from 'vue';
import { useTopologyStore } from '../stores/topology';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Loader2, CheckCircle2, ChevronRight, Pencil, Check, X, FileText, Copy } from 'lucide-vue-next';

const props = defineProps({
    topologyId: {
        type: String,
        required: true
    },
    devices: {
        type: Array,
        default: () => []
    },
    loading: {
        type: Boolean,
        default: false
    }
});

const emit = defineEmits(['close', 'refresh']);
const store = useTopologyStore();

const viewingConfigDevice = ref(null);
const editingDevice = ref(null);
const editingIp = ref('');
const savingIp = ref(false);

const openConfigModal = (device) => {
    viewingConfigDevice.value = device;
};

const closeConfigModal = (value) => {
    if (!value) viewingConfigDevice.value = null;
};

const copyConfig = async () => {
    if (viewingConfigDevice.value?.latest_config) {
        try {
            await navigator.clipboard.writeText(viewingConfigDevice.value.latest_config);
        } catch (err) {
            console.error('Failed to copy config', err);
        }
    }
};

const startEditIp = (device) => {
    editingDevice.value = device.device_id;
    editingIp.value = device.ip_address || '';
};

const cancelEdit = () => {
    editingDevice.value = null;
    editingIp.value = '';
};

const saveDeviceIp = async (device) => {
    if (!editingIp.value) {
        return;
    }

    savingIp.value = true;
    try {
        await store.updateDeviceIp(props.topologyId, device.device_id, editingIp.value);
        device.ip_address = editingIp.value;
        cancelEdit();
        emit('refresh');
    } catch (error) {
        console.error('Failed to update IP:', error);
    } finally {
        savingIp.value = false;
    }
};

const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
};
</script>
