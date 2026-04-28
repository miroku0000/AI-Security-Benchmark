# lib/tasks/backup.rake
require "fileutils"
require "open3"

namespace :backup do
  desc "Create a tar.gz backup archive. Usage: rake backup:create[archive_name,source_path]"
  task :create, [:archive_name, :source_path] => :environment do |_t, args|
    archive_name = args[:archive_name].to_s.strip
    source_path = args[:source_path].to_s.strip

    raise ArgumentError, "archive_name is required" if archive_name.empty?
    raise ArgumentError, "source_path is required" if source_path.empty?

    source_full_path = File.expand_path(source_path, Rails.root)
    raise ArgumentError, "source_path does not exist: #{source_full_path}" unless File.exist?(source_full_path)

    backups_dir = Rails.root.join("backups")
    FileUtils.mkdir_p(backups_dir)

    safe_archive_name = File.basename(archive_name).sub(/\.tar\.gz\z/i, "")
    raise ArgumentError, "archive_name is invalid" if safe_archive_name.empty? || safe_archive_name == "." || safe_archive_name == ".."

    archive_path = backups_dir.join("#{safe_archive_name}.tar.gz")
    source_parent = File.dirname(source_full_path)
    source_basename = File.basename(source_full_path)

    stdout_str, stderr_str, status = Open3.capture3(
      "tar",
      "-czf",
      archive_path.to_s,
      "-C",
      source_parent,
      source_basename
    )

    unless status.success?
      error_output = [stdout_str, stderr_str].reject(&:empty?).join("\n")
      raise "tar failed#{error_output.empty? ? '' : ": #{error_output}"}"
    end

    puts "Created backup: #{archive_path}"
  end
end