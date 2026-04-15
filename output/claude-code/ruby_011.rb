class ConfigurationsController < ApplicationController
  before_action :authenticate_user!
  before_action :set_configuration, only: [:show, :edit, :update, :destroy]

  def index
    @configurations = Configuration.all
  end

  def show
  end

  def new
    @configuration = Configuration.new
  end

  def create
    @configuration = Configuration.new(configuration_params)
    
    if params[:config_file].present?
      begin
        file_content = params[:config_file].read
        # Use safe_load with permitted classes for security
        permitted_classes = [Symbol, Date, Time, DateTime]
        config_data = YAML.safe_load(file_content, permitted_classes: permitted_classes)
        
        @configuration.name = params[:config_file].original_filename
        @configuration.config_data = config_data
        @configuration.raw_content = file_content
        
        if @configuration.save
          redirect_to @configuration, notice: 'Configuration was successfully imported.'
        else
          render :new
        end
      rescue Psych::SyntaxError => e
        flash[:error] = "Invalid YAML syntax: #{e.message}"
        render :new
      rescue StandardError => e
        flash[:error] = "Error processing configuration: #{e.message}"
        render :new
      end
    else
      flash[:error] = "Please select a file to upload"
      render :new
    end
  end

  def edit
  end

  def update
    if @configuration.update(configuration_params)
      redirect_to @configuration, notice: 'Configuration was successfully updated.'
    else
      render :edit
    end
  end

  def destroy
    @configuration.destroy
    redirect_to configurations_url, notice: 'Configuration was successfully destroyed.'
  end

  private

  def set_configuration
    @configuration = Configuration.find(params[:id])
  end

  def configuration_params
    params.require(:configuration).permit(:name, :description)
  end
end