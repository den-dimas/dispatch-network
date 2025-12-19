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
                                    <Input 
                                        v-if="editingDevice === device.device_id"
                                        v-model="editingIp"
                                        placeholder="192.168.1.1"
                                        class="h-8 text-sm"
                                        @keyup.enter="saveDeviceIp(device)"
                                        @keyup.escape="cancelEdit"
                                    />
                                    <span v-else class="text-sm">
                                        IP: {{ device.ip_address || 'Not set' }}
                                    </span>
                                    
                                    <Button 
                                        v-if="editingDevice === device.device_id"
                                        variant="ghost" 
                                        size="icon"
                                        class="h-6 w-6"
                                        @click="saveDeviceIp(device)"
                                        :disabled="savingIp"
                                    >
                                        <Loader2 v-if="savingIp" class="h-3 w-3 animate-spin" />
                                        <Check v-else class="h-3 w-3" />
                                    </Button>
                                    <Button 
                                        v-if="editingDevice === device.device_id"
                                        variant="ghost" 
                                        size="icon"
                                        class="h-6 w-6"
                                        @click="cancelEdit"
                                    >
                                        <X class="h-3 w-3" />
                                    </Button>
                                    <Button 
                                        v-else
                                        variant="ghost" 
                                        size="icon"
                                        class="h-6 w-6"
                                        @click="startEditIp(device)"
                                    >
                                        <Pencil class="h-3 w-3" />
                                    </Button>
                                </div>

                                <div v-if="device.latest_config" class="mt-3">
                                    <Button variant="outline" size="sm" @click="toggleConfig(device.device_id)"
                                        class="w-full justify-between">
                                        <span class="text-xs">View Config</span>
                                        <ChevronDown class="h-3 w-3 transition-transform"
                                            :class="{ 'rotate-180': expandedConfig === device.device_id }" />
                                    </Button>

                                    <div v-if="expandedConfig === device.device_id"
                                        class="mt-2 bg-muted border rounded p-3 max-h-96 overflow-y-auto">
                                        <div class="flex items-center justify-between mb-2">
                                            <span class="text-xs text-muted-foreground">
                                                Last updated: {{ formatDate(device.config_updated_at) }}
                                            </span>
                                        </div>
                                        <pre
                                            class="text-xs font-mono whitespace-pre-wrap break-all">{{ device.latest_config }}</pre>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
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
import { Loader2, CheckCircle2, ChevronDown, Pencil, Check, X } from 'lucide-vue-next';

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

const expandedConfig = ref(null);
const editingDevice = ref(null);
const editingIp = ref('');
const savingIp = ref(false);

const toggleConfig = (deviceId) => {
    expandedConfig.value = expandedConfig.value === deviceId ? null : deviceId;
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
