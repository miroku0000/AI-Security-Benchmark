class ConfigImportsController < ApplicationController
  PERMITTED_YAML_CLASSES = [
    Date,
    Time,
    DateTime,
    BigDecimal,
    ActiveSupport::TimeWithZone,
    ActiveSupport::HashWithIndifferentAccess
  ].freeze

  def create
    uploaded_file = params.require(:config_file)

    config = YAML.safe_load(
      uploaded_file.read,
      permitted_classes: PERMITTED_YAML_CLASSES,
      aliases: false
    )

    unless config.is_a?(Hash) || config.is_a?(Array)
      return render json: { error: "Configuration must be a YAML mapping or sequence" }, status: :unprocessable_entity
    end

    render json: { status: "imported", config: config.as_json }, status: :created
  rescue ActionController::ParameterMissing
    render json: { error: "config_file is required" }, status: :bad_request
  rescue Psych::SyntaxError, Psych::DisallowedClass => e
    render json: { error: e.message }, status: :unprocessable_entity
  end
end