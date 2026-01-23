<template>
  <div class="prompt-form">
    <div class="form-title">Custom Prompt & Template</div>

    <!-- Template Selector Section -->
    <div class="template-selector">
      <div class="section-title">Select a Template</div>
      <div class="template-grid">
        <button
          v-for="template in templates"
          :key="template.id"
          class="template-button"
          :class="{ active: selectedTemplate === template.id }"
          @click="selectTemplate(template)"
          @keydown.enter="selectTemplate(template)"
        >
          <div class="template-name">{{ template.name }}</div>
          <div class="template-desc">{{ template.description }}</div>
        </button>
      </div>

      <div v-if="selectedTemplate" class="template-info">
        <p>Selected: <strong>{{ getSelectedTemplateName }}</strong></p>
      </div>
    </div>

    <!-- Prompt Editor Section -->
    <div class="prompt-editor">
      <div class="section-title">Customize Your Prompt</div>

      <div class="editor-container">
        <label for="prompt-textarea">Prompt Text</label>
        <textarea
          id="prompt-textarea"
          class="prompt-textarea"
          v-model="customPrompt"
          placeholder="Enter your custom prompt using {{variable}} syntax..."
          rows="6"
        />
        <div class="char-count">{{ customPrompt.length }} characters</div>

        <div v-if="customPrompt.length > 1000" class="length-warning">
          ⚠️ Prompt is quite long. Consider making it more concise.
        </div>
      </div>

      <!-- Preview Section -->
      <div class="preview-section">
        <div class="preview-title">Current Prompt</div>
        <div class="prompt-preview">
          {{ previewPrompt }}
        </div>
      </div>
    </div>

    <!-- Variable Substitution Section -->
    <div class="variable-section">
      <div class="section-title">Variable Values</div>

      <div v-if="detectedVariables.length > 0" class="variables-grid">
        <div v-for="varName in detectedVariables" :key="varName" class="variable-input-group">
          <label :for="`var-${varName}`" class="variable-label">{{ varName }}</label>
          <input
            :id="`var-${varName}`"
            type="text"
            class="variable-input"
            :value="variableValues[varName] || ''"
            :placeholder="`Enter value for {{${varName}}}...`"
            @input="updateVariable(varName, $event)"
          />
        </div>
      </div>

      <div v-else class="no-variables">
        <p>No variables detected. Add {{variable}} placeholders to your prompt.</p>
      </div>
    </div>

    <!-- Form Actions -->
    <div class="form-actions">
      <button
        class="btn-generate"
        :disabled="customPrompt.trim().length === 0"
        @click="generatePrompt"
        aria-label="Generate image with this prompt"
      >
        🎨 Generate Image
      </button>

      <button
        class="btn-copy"
        :disabled="customPrompt.trim().length === 0"
        @click="copyPrompt"
        aria-label="Copy prompt to clipboard"
      >
        📋 Copy Prompt
      </button>

      <button class="btn-reset" @click="resetForm" aria-label="Reset form to defaults">
        🔄 Reset
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Template {
  id: string
  name: string
  description: string
  template: string
}

interface GeneratePayload {
  prompt: string
  variables: Record<string, string>
  selectedTemplate: string | null
}

const props = defineProps<{
  templates: Template[]
}>()

const emit = defineEmits<{
  generate: [payload: GeneratePayload]
  reset: []
  copy: []
}>()

const selectedTemplate = ref<string | null>(null)
const customPrompt = ref('')
const variableValues = ref<Record<string, string>>({})

// Detect variables in the format {{variable}}
const detectedVariables = computed(() => {
  const regex = /\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}/g
  const variables: Set<string> = new Set()
  let match

  while ((match = regex.exec(customPrompt.value)) !== null) {
    variables.add(match[1])
  }

  return Array.from(variables).sort()
})

// Generate preview with substituted variables
const previewPrompt = computed(() => {
  let preview = customPrompt.value

  detectedVariables.value.forEach((varName) => {
    const value = variableValues.value[varName] || `{{${varName}}}`
    preview = preview.replace(new RegExp(`\\{\\{${varName}\\}\\}`, 'g'), value)
  })

  return preview
})

// Get the name of selected template
const getSelectedTemplateName = computed(() => {
  if (!selectedTemplate.value) return ''
  const template = props.templates.find((t) => t.id === selectedTemplate.value)
  return template?.name || ''
})

// Select a template
const selectTemplate = (template: Template) => {
  selectedTemplate.value = template.id
  customPrompt.value = template.template
  variableValues.value = {}
}

// Update variable value
const updateVariable = (varName: string, event: Event) => {
  const target = event.target as HTMLInputElement
  variableValues.value[varName] = target.value
}

// Generate and emit event
const generatePrompt = () => {
  emit('generate', {
    prompt: customPrompt.value,
    variables: variableValues.value,
    selectedTemplate: selectedTemplate.value,
  })
}

// Copy prompt to clipboard
const copyPrompt = async () => {
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(previewPrompt.value)
    }
    emit('copy')
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

// Reset form
const resetForm = () => {
  selectedTemplate.value = null
  customPrompt.value = ''
  variableValues.value = {}
  emit('reset')
}
</script>

<style scoped>
.prompt-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px;
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.form-title {
  font-size: 20px;
  font-weight: 700;
  color: #333;
  margin-bottom: 8px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

/* Template Selector */
.template-selector {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.template-button {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  background-color: #f9f9f9;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: left;
}

.template-button:hover {
  border-color: #2196f3;
  background-color: #f0f7ff;
}

.template-button.active {
  border-color: #2196f3;
  background-color: #e3f2fd;
  box-shadow: 0 2px 4px rgba(33, 150, 243, 0.2);
}

.template-name {
  font-weight: 600;
  color: #333;
  font-size: 13px;
}

.template-desc {
  font-size: 11px;
  color: #999;
}

.template-info {
  font-size: 12px;
  color: #666;
  padding: 8px;
  background-color: #f5f5f5;
  border-radius: 4px;
}

/* Prompt Editor */
.prompt-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.editor-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.editor-container label {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.prompt-textarea {
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  resize: vertical;
  transition: border-color 0.3s ease;
}

.prompt-textarea:focus {
  outline: none;
  border-color: #2196f3;
  box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
}

.char-count {
  font-size: 12px;
  color: #999;
  text-align: right;
}

.length-warning {
  font-size: 12px;
  color: #ff9800;
  padding: 8px;
  background-color: #fff3e0;
  border-left: 3px solid #ff9800;
  border-radius: 4px;
}

/* Preview Section */
.preview-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background-color: #f5f5f5;
  border-radius: 6px;
}

.preview-title {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.prompt-preview {
  font-size: 13px;
  line-height: 1.6;
  color: #333;
  padding: 8px;
  background-color: #ffffff;
  border-radius: 4px;
  min-height: 60px;
  word-wrap: break-word;
  white-space: pre-wrap;
}

/* Variable Section */
.variable-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.variables-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.variable-input-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.variable-label {
  font-size: 12px;
  font-weight: 600;
  color: #333;
  font-family: 'Monaco', 'Courier New', monospace;
  background-color: #f0f0f0;
  padding: 2px 6px;
  border-radius: 3px;
  display: inline-block;
  width: fit-content;
}

.variable-input {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 13px;
  transition: border-color 0.3s ease;
}

.variable-input:focus {
  outline: none;
  border-color: #2196f3;
  box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.1);
}

.no-variables {
  padding: 16px;
  background-color: #f5f5f5;
  border-radius: 6px;
  text-align: center;
  color: #999;
  font-size: 13px;
}

/* Form Actions */
.form-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.form-actions button {
  flex: 1;
  min-width: 120px;
  padding: 12px 16px;
  font-size: 13px;
  font-weight: 600;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-generate {
  background-color: #2196f3;
  color: white;
  flex: 2;
}

.btn-generate:hover:not(:disabled) {
  background-color: #1976d2;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3);
}

.btn-generate:disabled {
  background-color: #ccc;
  cursor: not-allowed;
  color: #999;
}

.btn-copy {
  background-color: #4caf50;
  color: white;
}

.btn-copy:hover:not(:disabled) {
  background-color: #388e3c;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
}

.btn-copy:disabled {
  background-color: #ccc;
  cursor: not-allowed;
  color: #999;
}

.btn-reset {
  background-color: #f44336;
  color: white;
}

.btn-reset:hover {
  background-color: #d32f2f;
  box-shadow: 0 2px 8px rgba(244, 67, 54, 0.3);
}

/* Responsive */
@media (max-width: 768px) {
  .prompt-form {
    padding: 16px;
    gap: 16px;
  }

  .form-title {
    font-size: 18px;
  }

  .template-grid {
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  }

  .variables-grid {
    grid-template-columns: 1fr;
  }

  .form-actions {
    flex-direction: column;
  }

  .form-actions button {
    width: 100%;
  }

  .btn-generate {
    flex: 1;
  }

  .prompt-textarea {
    min-height: 100px;
  }
}
</style>
