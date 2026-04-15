class SendgridMailer < ApplicationMailer
  class DeliveryError < StandardError; end