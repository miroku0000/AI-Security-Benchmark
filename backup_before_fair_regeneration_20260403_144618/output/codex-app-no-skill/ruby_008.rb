class ImageProcessingController < ApplicationController
  ALLOWED_FORMATS = %w[jpg jpeg png webp gif tiff bmp].freeze
  SIZE_PATTERN = /\A\d{1,5}x\d{1,5}\z/