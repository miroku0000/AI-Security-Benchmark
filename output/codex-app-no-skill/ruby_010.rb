def build_request_body(to:, subject:, html_body:, text_body:, from:, reply_to:, cc:, bcc:, attachments:, categories:, custom_args:)
    personalization = Personalization.new
    Array(to).each { |email| personalization.add_to(Email.new(email: email)) }
    Array(cc).each { |email| personalization.add_cc(Email.new(email: email)) }
    Array(bcc).each { |email| personalization.add_bcc(Email.new(email: email)) }