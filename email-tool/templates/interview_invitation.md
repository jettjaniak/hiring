Dear `{{candidate.first_name}}`,

We're pleased to invite you to interview for the **`{{position}}`** position with our team!

## Interview Details

- **Date & Time:** `{{interview_date}}`
- **Format:** `{% if interview_type == "video" %}`Video call`{% elif interview_type == "phone" %}`Phone call`{% elif interview_type == "in_person" %}`In-person at our office`{% endif %}`
- **Interviewer:** `{{interviewer_name}}`
- **Duration:** Approximately 45-60 minutes

`{% if interview_type == "video" and zoom_link %}`
**Join video call:** `{{zoom_link}}`
`{% endif %}`

`{% if interview_type == "in_person" and office_address %}`
**Location:**
```
{{office_address}}
```
Please check in at the reception desk when you arrive.
`{% endif %}`

## What to Expect

During this interview, we'll:
- Discuss your experience and background in more detail
- Explore how your skills align with the role
- Answer any questions you have about the position and our company
- Provide an overview of next steps in the hiring process

Please feel free to prepare any questions you'd like to ask us. We're looking forward to speaking with you!

If you need to reschedule or have any questions, please reply to this email.

Best regards,  
**`{{sender_name}}`**
