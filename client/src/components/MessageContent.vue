<template>
    <div class="space-y-2">
        <template v-for="(section, idx) in parts" :key="idx">
            <!-- Thinking Process -->
            <div v-if="section.type === 'thinking'" class="rounded-lg border bg-muted/50 overflow-hidden">
                <button @click="toggleExpanded(idx)"
                    class="w-full flex items-center justify-between px-3 py-2 text-xs text-muted-foreground hover:bg-muted/80 transition-colors">
                    <div class="flex items-center gap-2">
                        <BrainCircuit class="h-3 w-3" />
                        <span>Thinking Process</span>
                    </div>
                    <ChevronDown class="h-3 w-3 transition-transform duration-200" :class="{ 'rotate-180': expandedSections[idx] }" />
                </button>

                <div v-show="expandedSections[idx]"
                    class="px-3 py-2 text-sm text-muted-foreground border-t bg-muted/30 whitespace-pre-wrap font-mono">
                    {{ section.content }}
                </div>
            </div>

            <!-- Todo List -->
            <div v-else-if="section.type === 'todo'" class="rounded-lg border bg-muted/50 p-3 space-y-2">
                <div class="flex items-center gap-2 text-xs font-semibold text-muted-foreground mb-2">
                    <ListTodo class="h-3 w-3" />
                    <span>Task List</span>
                </div>
                <div v-for="(item, todoIdx) in section.content" :key="todoIdx" class="flex items-center gap-2 text-sm">
                    <div class="w-4 h-4 rounded flex items-center justify-center" :class="item.completed ? 'bg-green-500/20 text-green-400' : 'bg-muted border'">
                        <Check v-if="item.completed" class="h-3 w-3" />
                    </div>
                    <span :class="item.completed ? 'text-muted-foreground line-through' : ''">{{ item.task }}</span>
                </div>
            </div>

            <!-- Configuration Proposal -->
            <div v-else-if="section.type === 'config'" class="rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3 space-y-3">
                <div class="flex items-center gap-2 text-xs font-semibold text-yellow-400 mb-2">
                    <Settings class="h-3 w-3" />
                    <span>Configuration Proposal</span>
                </div>
                
                <!-- Reasoning (shared across all devices) -->
                <div v-if="section.content.reasoning" class="text-sm text-yellow-200/90 bg-yellow-500/5 rounded p-2 border border-yellow-500/20">
                    <div class="text-xs text-muted-foreground mb-1">Reasoning:</div>
                    {{ section.content.reasoning }}
                </div>

                <!-- Legacy single device format -->
                <div v-if="section.content.device" class="text-sm space-y-2">
                    <div class="font-mono text-xs">
                        <span class="text-muted-foreground">Device:</span> 
                        <span class="text-yellow-300">{{ section.content.device }}</span>
                    </div>
                    <div v-if="section.content.parent" class="font-mono text-xs">
                        <span class="text-muted-foreground">Context:</span> 
                        <span class="text-blue-300">{{ section.content.parent }}</span>
                    </div>
                    <div v-if="section.content.commands && section.content.commands.length > 0" class="space-y-1">
                        <div class="text-muted-foreground text-xs">Commands:</div>
                        <div class="bg-black/40 rounded p-2 font-mono text-xs space-y-1">
                            <div v-for="(cmd, cmdIdx) in section.content.commands" :key="cmdIdx" class="text-green-300">
                                {{ cmd }}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- New multiple devices format -->
                <div v-if="section.content.devices" class="space-y-3">
                    <div v-for="(deviceConfig, devIdx) in section.content.devices" :key="devIdx" 
                         class="border border-yellow-500/20 rounded-lg p-3 bg-yellow-500/5 space-y-2">
                        <div class="font-mono text-xs font-semibold">
                            <span class="text-muted-foreground">Device:</span> 
                            <span class="text-yellow-300">{{ deviceConfig.device_name }}</span>
                        </div>
                        <div v-if="deviceConfig.parent" class="font-mono text-xs">
                            <span class="text-muted-foreground">Context:</span> 
                            <span class="text-blue-300">{{ deviceConfig.parent }}</span>
                        </div>
                        <div v-if="deviceConfig.commands && deviceConfig.commands.length > 0" class="space-y-1">
                            <div class="text-muted-foreground text-xs">Commands:</div>
                            <div class="bg-black/40 rounded p-2 font-mono text-xs space-y-1">
                                <div v-for="(cmd, cmdIdx) in deviceConfig.commands" :key="cmdIdx" class="text-green-300">
                                    {{ cmd }}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Regular Text/Markdown -->
            <div v-else-if="section.type === 'text'" class="prose prose-invert prose-slate max-w-none markdown-content text-sm" v-html="renderMarkdown(section.content)"></div>
        </template>
    </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { BrainCircuit, ChevronDown, ListTodo, Check, Settings } from 'lucide-vue-next';

const props = defineProps({
    content: {
        type: String,
        required: true
    },
    mode: {
        type: String,
        default: 'ask'
    }
});

const expandedSections = ref({});

const toggleExpanded = (idx) => {
    expandedSections.value[idx] = !expandedSections.value[idx];
};

const parts = computed(() => {
    const content = props.content;
    const sections = [];
    let currentPos = 0;

    const patterns = [
        { regex: /<think>([\s\S]*?)<\/think>/g, type: 'thinking', openTag: '<think>', closeTag: '</think>' },
        { regex: /<todo>([\s\S]*?)<\/todo>/g, type: 'todo', openTag: '<todo>', closeTag: '</todo>' },
        { regex: /<config_proposal>([\s\S]*?)<\/config_proposal>/g, type: 'config', openTag: '<config_proposal>', closeTag: '</config_proposal>' },
        { regex: /<tool_call>([\s\S]*?)<\/tool_call>/g, type: 'tool', openTag: '<tool_call>', closeTag: '</tool_call>' }
    ];

    const matches = [];
    
    patterns.forEach(pattern => {
        let match;
        const regex = new RegExp(pattern.regex.source, pattern.regex.flags);
        while ((match = regex.exec(content)) !== null) {
            matches.push({
                type: pattern.type,
                start: match.index,
                end: regex.lastIndex,
                content: match[1].trim(),
                closed: true
            });
        }
    });

    patterns.forEach(pattern => {
        let searchPos = 0;
        while (true) {
            const openIndex = content.indexOf(pattern.openTag, searchPos);
            if (openIndex === -1) break;
            
            const closeIndex = content.indexOf(pattern.closeTag, openIndex);
            
            const isAlreadyMatched = matches.some(m => 
                m.start === openIndex && m.closed === true
            );
            
            if (!isAlreadyMatched && closeIndex === -1) {
                const contentStart = openIndex + pattern.openTag.length;
                let contentEnd = content.length;
                
                const allOpenTags = patterns.map(p => p.openTag);
                for (const otherTag of allOpenTags) {
                    const nextTagIndex = content.indexOf(otherTag, contentStart);
                    if (nextTagIndex !== -1 && nextTagIndex < contentEnd) {
                        contentEnd = nextTagIndex;
                    }
                }
                
                const unclosedContent = content.substring(contentStart, contentEnd);
                matches.push({
                    type: pattern.type,
                    start: openIndex,
                    end: contentEnd,
                    content: unclosedContent.trim(),
                    closed: false
                });
                break;
            }
            
            searchPos = openIndex + pattern.openTag.length;
        }
    });

    matches.sort((a, b) => a.start - b.start);

    matches.forEach(match => {
        if (match.start > currentPos) {
            const textBefore = content.substring(currentPos, match.start).trim();
            if (textBefore) {
                sections.push({ type: 'text', content: textBefore });
            }
        }

        if (match.type === 'todo') {
            try {
                sections.push({ type: 'todo', content: JSON.parse(match.content) });
            } catch (e) {
                console.error('Failed to parse todo:', e);
            }
        } else if (match.type === 'config') {
            try {
                sections.push({ type: 'config', content: JSON.parse(match.content) });
            } catch (e) {
                console.error('Failed to parse config:', e);
            }
        } else {
            sections.push({ type: match.type, content: match.content });
        }

        currentPos = match.end;
    });

    if (currentPos < content.length) {
        const textAfter = content.substring(currentPos).trim();
        if (textAfter) {
            sections.push({ type: 'text', content: textAfter });
        }
    }

    return sections;
});

const renderMarkdown = (text) => {
    const rawHtml = marked.parse(text);
    return DOMPurify.sanitize(rawHtml);
};
</script>
