class ImageProcessorController < ApplicationController
  skip_before_action :verify_authenticity_token
  
  def upload
    render :upload_form
  end
  
  def process_image
    uploaded_file = params[:image]
    output_format = params[:format]
    size = params[:size]
    
    if uploaded_file && output_format
      timestamp = Time.now.to_i
      input_path = Rails.root.join('tmp', "input_#{timestamp}_#{uploaded_file.original_filename}")
      output_filename = "output_#{timestamp}.#{output_format}"
      output_path = Rails.root.join('public', 'processed', output_filename)
      
      FileUtils.mkdir_p(Rails.root.join('public', 'processed'))
      
      File.open(input_path, 'wb') do |file|
        file.write(uploaded_file.read)
      end
      
      convert_command = "convert #{input_path} "
      convert_command += "-resize #{size} " if size.present?
      convert_command += output_path.to_s
      
      system(convert_command)
      
      File.delete(input_path) if File.exist?(input_path)
      
      @processed_url = "/processed/#{output_filename}"
      render :result
    else
      redirect_to upload_path, alert: 'Please provide an image and format'
    end
  end
  
  def upload_form
    render html: <<-HTML.html_safe
      <html>
      <body>
        <h2>Image Processor</h2>
        <form action="/process_image" method="post" enctype="multipart/form-data">
          <div>
            <label>Select Image:</label>
            <input type="file" name="image" required>
          </div>
          <div>
            <label>Output Format:</label>
            <input type="text" name="format" placeholder="jpg, png, gif, etc" required>
          </div>
          <div>
            <label>Size (optional):</label>
            <input type="text" name="size" placeholder="800x600, 50%, etc">
          </div>
          <button type="submit">Process Image</button>
        </form>
      </body>
      </html>
    HTML
  end
  
  def result
    render html: <<-HTML.html_safe
      <html>
      <body>
        <h2>Processed Image</h2>
        <img src="#{@processed_url}" style="max-width: 100%;">
        <p><a href="#{@processed_url}" download>Download</a></p>
        <p><a href="/upload">Process Another Image</a></p>
      </body>
      </html>
    HTML
  end
end