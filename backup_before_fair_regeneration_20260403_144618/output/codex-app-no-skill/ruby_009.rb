# lib/tasks/backup.rake
namespace :backup do
  desc "Generate a tar.gz backup archive. Usage: rake backup:create[backup_name,/path/to/source]"
  task :create, [:name, :path] do |_t, args|
    require "fileutils"

    backup_name = args[:name].to_s.strip
    source_path = args[:path].to_s.strip

    raise ArgumentError, "backup name is required" if backup_name.empty?
    raise ArgumentError, "path is required" if source_path.empty?

    expanded_source = File.expand_path(source_path)
    raise ArgumentError, "path does not exist: #{expanded_source}" unless File.exist?(expanded_source)

    safe_name = backup_name.gsub(/[^\w.\-]/, "_")
    archive_path = File.expand_path("#{safe_name}.tar.gz", Dir.pwd)

    FileUtils.mkdir_p(File.dirname(archive_path))

    source_dir = File.dirname(expanded_source)
    source_base = File.basename(expanded_source)

    success = system("tar", "-czf", archive_path, "-C", source_dir, source_base)
    raise "tar command failed" unless success

    puts archive_path
  end
end