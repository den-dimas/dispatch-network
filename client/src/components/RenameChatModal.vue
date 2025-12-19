<template>
    <Dialog :open="true" @update:open="handleClose">
        <DialogContent class="sm:max-w-[425px]">
            <DialogHeader>
                <DialogTitle>Rename Chat Session</DialogTitle>
                <DialogDescription>
                    Enter a new title for this chat session.
                </DialogDescription>
            </DialogHeader>

            <div class="py-4">
                <div class="space-y-2">
                    <label for="title" class="text-sm font-medium">Title</label>
                    <Input id="title" v-model="newTitle" placeholder="Enter new title" @keyup.enter="handleRename"
                        :disabled="loading" />
                </div>
            </div>

            <DialogFooter>
                <Button type="button" variant="outline" @click="handleClose" :disabled="loading">Cancel</Button>
                <Button type="button" @click="handleRename" :disabled="loading || !newTitle.trim()">
                    <Loader2 v-if="loading" class="mr-2 h-4 w-4 animate-spin" />
                    Rename
                </Button>
            </DialogFooter>
        </DialogContent>
    </Dialog>
</template>

<script setup>
import { ref } from 'vue';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Loader2 } from 'lucide-vue-next';

const props = defineProps({
    session: {
        type: Object,
        required: true
    }
});

const emit = defineEmits(['close', 'rename']);

const loading = ref(false);
const newTitle = ref(props.session.title);

const handleRename = async () => {
    if (!newTitle.value.trim()) return;

    loading.value = true;
    try {
        emit('rename', newTitle.value.trim());
    } finally {
        loading.value = false;
    }
};

const handleClose = () => {
    if (!loading.value) {
        emit('close');
    }
};
</script>
