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
                    <ChevronDown class="h-3 w-3 transition-transform duration-200"
                        :class="{ 'rotate-180': expandedSections[idx] }" />
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
                    <div class="w-4 h-4 rounded flex items-center justify-center"
                        :class="item.completed ? 'bg-green-500/20 text-green-400' : 'bg-muted border'">
                        <Check v-if="item.completed" class="h-3 w-3" />
                    </div>
                    <span :class="item.completed ? 'text-muted-foreground line-through' : ''">{{ item.task }}</span>
                </div>
            </div>

            <!-- Configuration Proposal -->
            <div v-else-if="section.type === 'config'"
                class="rounded-lg border border-blue-200 bg-blue-50 p-4 space-y-3">
                <div class="flex items-center gap-2 text-xs font-semibold text-blue-600 mb-2">
                    <Settings class="h-4 w-4" />
                    <span>Configuration Proposal</span>
                </div>

                <div class="prose prose-slate prose-sm max-w-none 
                prose-h3:text-blue-700 prose-h3:font-bold prose-h3:text-lg prose-h3:mt-4 prose-h3:mb-2 prose-h3:border-b prose-h3:border-blue-200 prose-h3:pb-1
                prose-code:bg-gray-200 prose-code:text-blue-700 prose-code:font-mono prose-code:px-1 prose-code:rounded
                prose-pre:bg-gray-900 prose-pre:text-gray-50 prose-pre:border prose-pre:border-gray-200 prose-pre:shadow-sm"
                    v-html="renderMarkdown(section.content)">
                </div>
            </div>

            <!-- Regular Text/Markdown -->
            <div v-else-if="section.type === 'text'" class="prose prose-slate max-w-none markdown-content text-sm text-foreground
                prose-headings:text-foreground prose-p:text-foreground prose-strong:text-foreground prose-li:text-foreground
                prose-code:bg-muted prose-code:text-primary prose-pre:bg-muted/50 prose-pre:text-foreground"
                v-html="renderMarkdown(section.content)"></div>
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

            const isInsideClosed = matches.some(m =>
                openIndex > m.start && openIndex < m.end
            );

            if (isInsideClosed) {

                searchPos = openIndex + pattern.openTag.length;
                continue;
            }

            const isAlreadyMatched = matches.some(m =>
                m.start === openIndex && m.closed === true
            );

            if (!isAlreadyMatched && closeIndex === -1) {

                const contentStart = openIndex + pattern.openTag.length;
                matches.push({
                    type: pattern.type,
                    start: openIndex,
                    end: content.length,
                    content: content.substring(contentStart).trim(),
                    closed: false
                });
                break;
            }

            searchPos = openIndex + pattern.openTag.length;
        }
    });

    matches.sort((a, b) => a.start - b.start);

    matches.forEach(match => {

        if (match.start < currentPos) return;

        if (match.start > currentPos) {
            const textBefore = content.substring(currentPos, match.start).trim();
            if (textBefore) {
                sections.push({ type: 'text', content: textBefore });
            }
        }

        if (match.type === 'todo') {
            try {
                sections.push({ type: 'todo', content: JSON.parse(match.content) });
            } catch (e) { }
        } else if (match.type === 'config') {

            sections.push({ type: 'config', content: match.content });
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
