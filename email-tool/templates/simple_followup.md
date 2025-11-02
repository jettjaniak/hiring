Dear `{{candidate.first_name}}`,

Thank you for taking the time to meet with us on **`{{meeting_date}}`**. We enjoyed learning more about your background and experience.

`{% if next_steps == "technical_interview" %}`
Based on our conversation, we'd like to invite you to a technical interview as the next step. Our team will reach out shortly with available time slots.
`{% elif next_steps == "reference_check" %}`
We're moving forward with your application and would like to conduct reference checks. Please provide us with contact information for 2-3 professional references.
`{% elif next_steps == "offer_coming" %}`
We're pleased to inform you that we're preparing an offer for you. Our team is working on the details and we'll be in touch within the next few days.
`{% endif %}`

Thank you again for your interest in joining our team.

Best regards,  
**`{{sender_name}}`**
