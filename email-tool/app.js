class EmailTemplateApp {
    constructor() {
        this.candidates = [];
        this.templates = {};
        this.templateBodies = {};
        this.currentTemplateKey = null;
        this.currentCandidate = null;
        this.variableValues = {};
        this.renderedTo = '';
        this.renderedCc = '';
        this.renderedBcc = '';
        this.renderedSubject = '';
        this.renderedBody = '';
        this.renderedHtml = '';
    }
    
    async init() {
        try {
            await this.loadCandidates();
            await this.loadTemplateIndex();
            this.setupEventListeners();
        } catch (error) {
            this.showError('Initialization Error', error.message);
        }
    }
    
    async loadCandidates() {
        const response = await fetch('candidates.yaml');
        if (!response.ok) {
            throw new Error(`Failed to load candidates.yaml: ${response.statusText}`);
        }
        const text = await response.text();
        const data = jsyaml.load(text);
        this.candidates = data.candidates;
        
        if (!Array.isArray(this.candidates) || this.candidates.length === 0) {
            throw new Error('candidates.yaml must contain a "candidates" array with at least one candidate');
        }
        
        // Validate candidates
        this.candidates.forEach((candidate, index) => {
            if (!candidate.email) {
                throw new Error(`Candidate at index ${index} is missing required field: email`);
            }
            if (!candidate.first_name) {
                throw new Error(`Candidate with email ${candidate.email} is missing required field: first_name`);
            }
            if (!candidate.full_name) {
                throw new Error(`Candidate with email ${candidate.email} is missing required field: full_name`);
            }
        });
        
        // Populate candidate dropdown
        const candidateSelect = document.getElementById('candidate-select');
        candidateSelect.innerHTML = '<option value="">-- Select Candidate --</option>';
        this.candidates.forEach(candidate => {
            const option = document.createElement('option');
            option.value = candidate.email;
            option.textContent = `${candidate.full_name} (${candidate.email})`;
            candidateSelect.appendChild(option);
        });
    }
    
    async loadTemplateIndex() {
        const response = await fetch('templates/index.yaml');
        if (!response.ok) {
            throw new Error(`Failed to load templates/index.yaml: ${response.statusText}`);
        }
        const text = await response.text();
        const data = jsyaml.load(text);
        
        if (!Array.isArray(data.templates) || data.templates.length === 0) {
            throw new Error('templates/index.yaml must contain a "templates" array with at least one template');
        }
        
        // Load each template
        const templateSelect = document.getElementById('template-select');
        templateSelect.innerHTML = '<option value="">-- Select Template --</option>';
        
        for (const templateKey of data.templates) {
            try {
                await this.loadTemplate(templateKey);
                
                // Add to dropdown
                const option = document.createElement('option');
                option.value = templateKey;
                option.textContent = this.templates[templateKey].name;
                templateSelect.appendChild(option);
            } catch (error) {
                console.error(`Failed to load template ${templateKey}:`, error);
                // Continue loading other templates instead of failing completely
            }
        }
        
        if (Object.keys(this.templates).length === 0) {
            throw new Error('No templates could be loaded successfully');
        }
    }
    
    async loadTemplate(templateKey) {
        // Load metadata
        const metadataResponse = await fetch(`templates/${templateKey}.yaml`);
        if (!metadataResponse.ok) {
            throw new Error(`Failed to load templates/${templateKey}.yaml: ${metadataResponse.statusText}`);
        }
        const metadataText = await metadataResponse.text();
        const metadata = jsyaml.load(metadataText);
        
        // Validate metadata
        if (!metadata.name) {
            throw new Error(`Template ${templateKey}.yaml is missing required field: name`);
        }
        if (!metadata.to) {
            throw new Error(`Template ${templateKey}.yaml is missing required field: to`);
        }
        if (!metadata.subject) {
            throw new Error(`Template ${templateKey}.yaml is missing required field: subject`);
        }
        
        this.templates[templateKey] = metadata;
        
        // Load body
        const bodyResponse = await fetch(`templates/${templateKey}.md`);
        if (!bodyResponse.ok) {
            throw new Error(`Failed to load templates/${templateKey}.md: ${bodyResponse.statusText}`);
        }
        this.templateBodies[templateKey] = await bodyResponse.text();
    }
    
    setupEventListeners() {
        document.getElementById('template-select').addEventListener('change', (e) => {
            this.onTemplateChange(e.target.value);
        });
        
        document.getElementById('candidate-select').addEventListener('change', (e) => {
            this.onCandidateChange(e.target.value);
        });
        
        document.getElementById('copy-btn').addEventListener('click', () => {
            this.copyToClipboard();
        });
        
        document.getElementById('mailto-btn').addEventListener('click', () => {
            this.openMailto();
        });
    }
    
    onTemplateChange(templateKey) {
        if (!templateKey) {
            this.currentTemplateKey = null;
            this.updatePreview();
            return;
        }
        
        try {
            this.currentTemplateKey = templateKey;
            this.variableValues = {};
            this.buildVariableControls();
            this.updatePreview();
        } catch (error) {
            this.showError('Template Change Error', error.message);
        }
    }
    
    onCandidateChange(email) {
        if (!email) {
            this.currentCandidate = null;
            this.updatePreview();
            return;
        }
        
        this.currentCandidate = this.candidates.find(c => c.email === email);
        if (!this.currentCandidate) {
            this.showError('Candidate Error', `Candidate with email ${email} not found`);
            return;
        }
        
        this.updatePreview();
    }
    
    buildVariableControls() {
        const container = document.getElementById('variable-controls');
        container.innerHTML = '';
        
        if (!this.currentTemplateKey) return;
        
        const template = this.templates[this.currentTemplateKey];
        if (!template.variables) return;
        
        Object.entries(template.variables).forEach(([varName, varConfig]) => {
            const formGroup = document.createElement('div');
            formGroup.className = 'form-group';
            
            if (varConfig.type === 'choice') {
                const label = document.createElement('label');
                label.textContent = varConfig.label || varName;
                label.htmlFor = `var-${varName}`;
                
                const select = document.createElement('select');
                select.id = `var-${varName}`;
                
                const emptyOption = document.createElement('option');
                emptyOption.value = '';
                emptyOption.textContent = '-- Select --';
                select.appendChild(emptyOption);
                
                varConfig.options.forEach(opt => {
                    const option = document.createElement('option');
                    option.value = opt.value;
                    option.textContent = opt.label;
                    select.appendChild(option);
                });
                
                if (varConfig.default) {
                    select.value = varConfig.default;
                    this.variableValues[varName] = varConfig.default;
                }
                
                select.addEventListener('change', (e) => {
                    this.variableValues[varName] = e.target.value;
                    this.updatePreview();
                });
                
                formGroup.appendChild(label);
                formGroup.appendChild(select);
                
            } else if (varConfig.type === 'boolean') {
                const checkboxGroup = document.createElement('div');
                checkboxGroup.className = 'checkbox-group';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `var-${varName}`;
                checkbox.checked = varConfig.default || false;
                this.variableValues[varName] = checkbox.checked;
                
                checkbox.addEventListener('change', (e) => {
                    this.variableValues[varName] = e.target.checked;
                    this.updatePreview();
                });
                
                const label = document.createElement('label');
                label.textContent = varConfig.label || varName;
                label.htmlFor = `var-${varName}`;
                
                checkboxGroup.appendChild(checkbox);
                checkboxGroup.appendChild(label);
                formGroup.appendChild(checkboxGroup);
                
            } else if (varConfig.type === 'text') {
                const label = document.createElement('label');
                label.textContent = varConfig.label || varName;
                label.htmlFor = `var-${varName}`;
                
                const input = document.createElement('input');
                input.type = 'text';
                input.id = `var-${varName}`;
                input.placeholder = varConfig.placeholder || '';
                input.value = varConfig.default || '';
                this.variableValues[varName] = input.value;
                
                input.addEventListener('input', (e) => {
                    this.variableValues[varName] = e.target.value;
                    this.updatePreview();
                });
                
                formGroup.appendChild(label);
                formGroup.appendChild(input);
            }
            
            container.appendChild(formGroup);
        });
    }
    
    updatePreview() {
        const metadataContainer = document.getElementById('metadata-container');
        const previewContainer = document.getElementById('email-preview');
        const copyBtn = document.getElementById('copy-btn');
        const mailtoBtn = document.getElementById('mailto-btn');
        
        if (!this.currentCandidate || !this.currentTemplateKey) {
            metadataContainer.innerHTML = '<div class="loading">Select a template and candidate to begin</div>';
            previewContainer.innerHTML = '<div class="loading">Email preview will appear here</div>';
            copyBtn.disabled = true;
            mailtoBtn.disabled = true;
            return;
        }
        
        try {
            const template = this.templates[this.currentTemplateKey];
            const templateBody = this.templateBodies[this.currentTemplateKey];
            
            // Build context
            const context = {
                candidate: this.currentCandidate,
                ...this.variableValues
            };
            
            // Configure Nunjucks
            nunjucks.configure({ autoescape: false, throwOnUndefined: true });
            
            // Render To
            try {
                this.renderedTo = nunjucks.renderString(template.to, context).trim();
            } catch (error) {
                throw new Error(`Error rendering 'to' field: ${error.message}`);
            }
            
            // Render CC
            this.renderedCc = '';
            if (template.cc) {
                try {
                    if (Array.isArray(template.cc)) {
                        this.renderedCc = template.cc
                            .map(cc => nunjucks.renderString(cc, context).trim())
                            .filter(cc => cc)
                            .join('; ');
                    } else {
                        this.renderedCc = nunjucks.renderString(template.cc, context).trim();
                    }
                } catch (error) {
                    throw new Error(`Error rendering 'cc' field: ${error.message}`);
                }
            }
            
            // Render BCC
            this.renderedBcc = '';
            if (template.bcc) {
                try {
                    if (Array.isArray(template.bcc)) {
                        this.renderedBcc = template.bcc
                            .map(bcc => nunjucks.renderString(bcc, context).trim())
                            .filter(bcc => bcc)
                            .join('; ');
                    } else {
                        this.renderedBcc = nunjucks.renderString(template.bcc, context).trim();
                    }
                } catch (error) {
                    throw new Error(`Error rendering 'bcc' field: ${error.message}`);
                }
            }
            
            // Render Subject
            try {
                this.renderedSubject = nunjucks.renderString(template.subject, context).trim();
            } catch (error) {
                throw new Error(`Error rendering 'subject' field: ${error.message}`);
            }
            
            // Process template body: replace `{% ... %}` with {% ... %}
            let processedBody = templateBody.replace(/`(\{[%{].*?[%}]\})`/g, '$1');
            
            // Render template with Nunjucks
            try {
                this.renderedBody = nunjucks.renderString(processedBody, context);
            } catch (error) {
                throw new Error(`Error rendering template body: ${error.message}\n\nCheck your template syntax and make sure all variables are defined.`);
            }
            
            // Convert markdown to HTML
            this.renderedHtml = marked.parse(this.renderedBody);
            
            // Update metadata display
            let metadataHtml = `
                <div class="metadata-item">
                    <span class="metadata-label">To:</span>
                    <span class="metadata-value">${this.escapeHtml(this.renderedTo)}</span>
                </div>`;
            
            if (this.renderedCc) {
                metadataHtml += `
                <div class="metadata-item">
                    <span class="metadata-label">CC:</span>
                    <span class="metadata-value">${this.escapeHtml(this.renderedCc)}</span>
                </div>`;
            }
            
            if (this.renderedBcc) {
                metadataHtml += `
                <div class="metadata-item">
                    <span class="metadata-label">BCC:</span>
                    <span class="metadata-value">${this.escapeHtml(this.renderedBcc)}</span>
                </div>`;
            }
            
            metadataHtml += `
                <div class="metadata-item">
                    <span class="metadata-label">Subject:</span>
                    <span class="metadata-value">${this.escapeHtml(this.renderedSubject)}</span>
                </div>`;
            
            metadataContainer.innerHTML = metadataHtml;
            
            // Update preview
            previewContainer.innerHTML = this.renderedHtml;
            
            // Enable buttons
            copyBtn.disabled = false;
            mailtoBtn.disabled = false;
            
        } catch (error) {
            this.showError('Rendering Error', error.message);
            copyBtn.disabled = true;
            mailtoBtn.disabled = true;
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    markdownToPlainText(markdown) {
        // Convert markdown to HTML first
        const html = marked.parse(markdown);
        
        // Create a temporary div to convert HTML to plain text
        const temp = document.createElement('div');
        temp.innerHTML = html;
        
        // Get text content (strips all HTML tags)
        return temp.textContent || temp.innerText || '';
    }
    
    async copyToClipboard() {
        try {
            await navigator.clipboard.write([
                new ClipboardItem({
                    'text/html': new Blob([this.renderedHtml], { type: 'text/html' }),
                    'text/plain': new Blob([this.renderedBody], { type: 'text/plain' })
                })
            ]);
            
            const btn = document.getElementById('copy-btn');
            const originalText = btn.textContent;
            btn.textContent = '✓ Copied!';
            btn.style.background = '#28a745';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.background = '';
            }, 2000);
            
        } catch (error) {
            this.showError('Clipboard Error', `Failed to copy to clipboard: ${error.message}`);
        }
    }
    
    async openMailto() {
        try {
            // First, copy the HTML body to clipboard so user can paste immediately
            const plainText = this.renderedBody;
            
            try {
                await navigator.clipboard.write([
                    new ClipboardItem({
                        'text/html': new Blob([this.renderedHtml], { type: 'text/html' }),
                        'text/plain': new Blob([plainText], { type: 'text/plain' })
                    })
                ]);
            } catch (clipError) {
                console.warn('Failed to copy to clipboard:', clipError);
                // Continue anyway - mailto will still work
            }
            
            // Build mailto URL WITHOUT body (using semicolons for multiple recipients)
            let mailto = `mailto:${encodeURIComponent(this.renderedTo)}?`;
            
            const params = [];
            
            if (this.renderedCc) {
                // Use semicolon as separator for multiple emails (RFC 6068)
                const ccEmails = this.renderedCc.replace(/,\s*/g, ';');
                params.push(`cc=${encodeURIComponent(ccEmails)}`);
            }
            
            if (this.renderedBcc) {
                // Use semicolon as separator for multiple emails (RFC 6068)
                const bccEmails = this.renderedBcc.replace(/,\s*/g, ';');
                params.push(`bcc=${encodeURIComponent(bccEmails)}`);
            }
            
            params.push(`subject=${encodeURIComponent(this.renderedSubject)}`);
            // Note: NO body parameter - user will paste from clipboard
            
            mailto += params.join('&');
            
            // Open mailto link
            window.location.href = mailto;
            
            // Visual feedback
            const btn = document.getElementById('mailto-btn');
            const originalText = btn.textContent;
            btn.textContent = '✓ Opened! Body copied - paste it';
            btn.style.background = '#28a745';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.background = '';
            }, 4000);
            
        } catch (error) {
            this.showError('Mailto Error', error.message);
        }
    }
    
    showError(title, message) {
        const metadataContainer = document.getElementById('metadata-container');
        const previewContainer = document.getElementById('email-preview');
        
        const errorHtml = `
            <div class="error">
                <div class="error-title">❌ ${this.escapeHtml(title)}</div>
                <div class="error-details">${this.escapeHtml(message)}</div>
            </div>
        `;
        
        metadataContainer.innerHTML = errorHtml;
        previewContainer.innerHTML = '';
        
        console.error(`${title}:`, message);
    }
}

// Initialize app when page loads
const app = new EmailTemplateApp();
app.init();
