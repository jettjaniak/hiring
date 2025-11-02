# Email Template Tool

A browser-based tool for creating templated emails with conditional content, supporting multiple recipients (CC/BCC) and markdown formatting.

## Quick Start

1. **Extract the zip file**
2. **Start a web server** in the extracted directory:
   ```bash
   python -m http.server 8000
   ```
3. **Open in browser:** http://localhost:8000/

## Features

✅ Template-based email generation  
✅ Conditional content with Jinja2 syntax  
✅ Markdown to HTML conversion  
✅ Multiple CC and BCC support  
✅ Live preview  
✅ Copy formatted HTML to clipboard  
✅ Generate mailto: links (with proper space encoding)  
✅ Loud error handling  
✅ No default template selection - choose what you need  

## File Structure

```
email-tool/
├── index.html              # Main page
├── style.css               # All styles
├── app.js                  # All JavaScript
├── candidates.yaml         # Candidate data
└── templates/
    ├── index.yaml          # List of templates
    ├── *.yaml              # Template metadata
    └── *.md                # Template bodies
```

## Usage

### 1. Select Template
Choose a template from the dropdown (nothing selected by default)

### 2. Select Candidate
Choose a candidate from the dropdown

### 3. Fill Variables
Complete the form fields for your selected template

### 4. Preview & Send
- **Copy HTML to Clipboard:** Copy formatted version to paste into Outlook
- **Open in Email Client:** Opens mailto: link with To, CC, BCC, Subject, and body

## Templates Included

1. **Simple Follow-up** - Basic follow-up email (no CC/BCC)
2. **Rejection After Interview** - Rejection with optional feedback (no CC/BCC)
3. **Phone Screening Invitation** - Interview invitation with CC to 2 addresses
4. **Team Notification** - New hire announcement with 3 CC and 2 BCC addresses

## What's Fixed

✅ **No default template** - Dropdown starts empty, you choose what you need  
✅ **Proper mailto encoding** - Spaces are encoded correctly (not as + symbols)  
✅ **Markdown to HTML** - All markdown formatting converted properly  
✅ **Multiple CC/BCC** - Support for arrays of recipients  
✅ **Separated files** - HTML, CSS, and JS in separate files for maintainability  

## Editing Candidates

Edit `candidates.yaml`:

```yaml
candidates:
  - email: "person@example.com"
    first_name: "FirstName"
    full_name: "Full Name"
```

All three fields are required.

## Creating Templates

### 1. Create Metadata File (`.yaml`)

```yaml
name: "Template Display Name"
to: "{{candidate.email}}"
cc: 
  - "person1@example.com"
  - "person2@example.com"
bcc:
  - "analytics@example.com"
subject: "Subject with {{variables}}"

variables:
  variable_name:
    type: "choice"  # or "boolean" or "text"
    label: "Label for UI"
    options:  # for choice type
      - value: "option1"
        label: "Option 1"
    default: "value"  # optional
```

### 2. Create Body File (`.md`)

Use Markdown with Jinja2 wrapped in backticks:

```markdown
Dear `{{candidate.first_name}}`,

`{% if variable_name == "option1" %}`
This appears when option1 is selected.
`{% endif %}`

Best regards,  
**Your Name**
```

**Why backticks?** Prevents autocorrect in editors like Obsidian.

### 3. Add to Index

Edit `templates/index.yaml`:

```yaml
templates:
  - existing_template
  - your_new_template  # Add here
```

## Markdown Support

The tool converts Markdown to HTML:

- **Bold:** `**text**`
- *Italic:* `*text*`
- Links: `[text](url)`
- Lists: `- item` or `1. item`
- Headers: `# H1`, `## H2`

## Jinja2 Syntax

```
`{% if condition %}`
  Content
`{% elif other_condition %}`
  Other content
`{% else %}`
  Default
`{% endif %}`
```

## CC and BCC Examples

**Single recipient:**
```yaml
cc: "person@example.com"
```

**Multiple recipients:**
```yaml
cc:
  - "person1@example.com"
  - "person2@example.com"
  - "person3@example.com"
```

**Template variables:**
```yaml
cc: "{{candidate.manager_email}}"
```

**Empty (no CC/BCC):**
```yaml
cc: []
bcc: []
```

## Mailto Link Behavior

- To, CC, BCC, Subject: Populated automatically
- Body: Plain text (Markdown formatting removed)
- Spaces: Properly encoded as %20 (not + symbols)
- Long emails (>2000 chars): Warning shown

**Recommended:** Use "Copy HTML to Clipboard" for long or formatted emails.

## Error Handling

The tool **fails loudly** with detailed messages:

- Missing files
- Invalid YAML syntax
- Undefined template variables
- Missing candidate fields

Check browser console (F12) for additional details.

## Troubleshooting

**"Failed to load" errors:**
- Make sure you're using a web server (not file://)
- Check file paths match exactly (case-sensitive)
- Verify all files from zip are extracted

**Templates not appearing:**
- Check `templates/index.yaml` lists your template
- Verify both `.yaml` and `.md` files exist
- Check browser console for errors

**Markdown not rendering:**
- Ensure backticks wrap Jinja2 syntax correctly
- Check for unclosed Jinja2 tags
- Verify template variables are defined

**Plus signs instead of spaces in mailto:**
- This was a bug in previous versions, now fixed
- Spaces are properly encoded as %20

## Browser Requirements

- Modern browser (Chrome, Firefox, Edge, Safari)
- JavaScript enabled
- Clipboard API support (for copy functionality)

## Tips

- Keep emails under 2000 characters for reliable mailto: links
- Test with different candidates to catch template errors
- Use browser DevTools (F12) to debug issues
- Backticks prevent Obsidian autocorrect on template syntax
- If a template file is missing, other templates will still load

## License

MIT - Use freely for personal or commercial projects
