module Webhooks
  class SendgridController < ApplicationController
    skip_before_action :verify_authenticity_token
    before_action :verify_webhook_signature
    
    def events
      params['_json'].each do |event|
        process_event(event)
      end
      
      head :ok
    rescue => e
      Rails.logger.error "SendGrid webhook error: #{e.message}"
      head :bad_request
    end
    
    private
    
    def verify_webhook_signature
      unless SendGridHelper.verify_webhook(request)
        head :unauthorized
        return false
      end
    end
    
    def process_event(event)
      case event['event']
      when 'delivered'
        handle_delivered(event)
      when 'bounce'
        handle_bounce(event)
      when 'dropped'
        handle_dropped(event)
      when 'spam_report'
        handle_spam_report(event)
      when 'unsubscribe'
        handle_unsubscribe(event)
      when 'open'
        handle_open(event)
      when 'click'
        handle_click(event)
      end
    end
    
    def handle_delivered(event)
      EmailLog.create!(
        email: event['email'],
        event: 'delivered',
        timestamp: Time.at(event['timestamp']),
        message_id: event['sg_message_id'],
        metadata: event.to_json
      )
    end
    
    def handle_bounce(event)
      EmailLog.create!(
        email: event['email'],
        event: 'bounce',
        timestamp: Time.at(event['timestamp']),
        message_id: event['sg_message_id'],
        reason: event['reason'],
        metadata: event.to_json
      )
      
      if event['type'] == 'blocked'
        User.where(email: event['email']).update_all(email_blocked: true)
      end
    end
    
    def handle_dropped(event)
      EmailLog.create!(
        email: event['email'],
        event: 'dropped',
        timestamp: Time.at(event['timestamp']),
        message_id: event['sg_message_id'],
        reason: event['reason'],
        metadata: event.to_json
      )
    end
    
    def handle_spam_report(event)
      EmailLog.create!(
        email: event['email'],
        event: 'spam_report',
        timestamp: Time.at(event['timestamp']),
        message_id: event['sg_message_id'],
        metadata: event.to_json
      )
      
      User.where(email: event['email']).update_all(marked_as_spam: true)
    end
    
    def handle_unsubscribe(event)
      EmailLog.create!(
        email: event['email'],
        event: 'unsubscribe',
        timestamp: Time.at(event['timestamp']),
        message_id: event['sg_message_id'],
        metadata: event.to_json
      )
      
      User.where(email: event['email']).update_all(unsubscribed: true)
    end
    
    def handle_open(event)
      EmailLog.create!(
        email: event['email'],
        event: 'open',
        timestamp: Time.at(event['timestamp']),
        message_id: event['sg_message_id'],
        user_agent: event['useragent'],
        ip: event['ip'],
        metadata: event.to_json
      )
    end
    
    def handle_click(event)
      EmailLog.create!(
        email: event['email'],
        event: 'click',
        timestamp: Time.at(event['timestamp']),
        message_id: event['sg_message_id'],
        url: event['url'],
        user_agent: event['useragent'],
        ip: event['ip'],
        metadata: event.to_json
      )
    end
  end
end