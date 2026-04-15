require "pathname"
require "fileutils"

namespace :backup do
  desc "Create a compressed tar backup. Usage: rake 'backup:create[name,/path/to/source]'"
  task :create, [:name, :path] do |_task, args|
    backup_name = args[:name].to_s.strip
    source_arg = args[:path].to_s.strip

    raise ArgumentError, "backup name is required" if backup_name.empty?
    raise ArgumentError, "backup path is required" if source_arg.empty?
    raise ArgumentError, "invalid backup name" unless backup_name.match?(/\A[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}\z/)
    raise ArgumentError, "backup name cannot end with dot" if backup_name.end_with?(".")

    source_path = Pathname.new(source_arg).realpath
    raise ArgumentError, "backup path does not exist" unless source_path.exist?

    output_dir = Pathname.new(Dir.pwd).realpath
    raise ArgumentError, "output directory is not writable" unless output_dir.directory? && output_dir.writable?

    archive_path = output_dir.join("#{backup_name}.tar.gz")
    raise ArgumentError, "archive already exists: #{archive_path}" if archive_path.exist?

    source_parent = source_path.dirname.to_s
    source_entry = source_path.basename.to_s
    temp_archive_path = output_dir.join(".#{backup_name}.#{Process.pid}.tmp.tar.gz")

    previous_umask = File.umask(0o077)

    begin
      reader, writer = IO.pipe

      pid = fork do
        begin
          reader.close
          STDOUT.reopen(writer)
          STDERR.reopen(writer)
          writer.close
          exec("tar", "tar", "-czf", temp_archive_path.to_s, "-C", source_parent, "--", source_entry)
        rescue SystemCallError => e
          warn("failed to execute tar: #{e.message}")
          exit!(127)
        end
      end

      writer.close
      output = reader.read
      reader.close

      _, status = Process.wait2(pid)

      unless status.success?
        File.delete(temp_archive_path) if temp_archive_path.exist?
        raise RuntimeError, output.empty? ? "tar failed with exit status #{status.exitstatus}" : output
      end

      File.rename(temp_archive_path, archive_path)
      puts archive_path.to_s
    ensure
      File.umask(previous_umask)
      File.delete(temp_archive_path) if temp_archive_path.exist?
    end
  end
end