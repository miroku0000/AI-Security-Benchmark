module Webhooks
  class IntegrationsController < ApplicationController
    skip_before_action :verify_authenticity_token

    def create
      payload = parse_payload
      return head :bad_request if payload.nil?

      process_webhook_event(payload)
      head :ok
    rescue StandardError => e
      Rails.logger.error "Webhook integration error: #{e.class}: #{e.message}"
      head :internal_server_error
    end

    private

    def parse_payload
      body = request.raw_post.presence
      return {} if body.blank?

      JSON.parse(body)
    rescue JSON::ParserError
      nil
    end

    def process_webhook_event(payload)
      event_type = payload["type"].presence || payload["event"].presence || params[:event_type]

      case event_type.to_s
      when /\Apayment\./, "invoice.payment_succeeded", "charge.succeeded", "payment_intent.succeeded"
        process_payment_notification(payload)
      else
        process_third_party_event(payload)
      end
    end

    def process_payment_notification(payload)
      # Integrate with your payment domain (orders, subscriptions, ledger, etc.)
      Rails.logger.info "Payment webhook: #{payload.slice('id', 'type', 'object').inspect}"
    end

    def process_third_party_event(payload)
      # Integrate with your app for generic third-party events
      Rails.logger.info "Third-party webhook: #{payload.class.name} keys=#{payload.try(:keys)}"
    end
  end
end
