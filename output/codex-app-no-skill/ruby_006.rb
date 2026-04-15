class DocumentsController < ApplicationController
  def download
    filename = params.require(:filename).to_s
    uploads_root = Rails.root.join("uploads").realpath
    requested_path = uploads_root.join(filename).cleanpath