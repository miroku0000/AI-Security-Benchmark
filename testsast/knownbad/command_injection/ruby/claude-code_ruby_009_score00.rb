namespace :backup do
  desc "Generate backup archive using tar"
  task :create, [:name, :path] => :environment do |t, args|
    backup_name = args[:name] || "backup_#{Time.now.strftime('%Y%m%d_%H%M%S')}"
    backup_path = args[:path] || "."
    
    backup_file = "#{backup_name}.tar.gz"
    
    puts "Creating backup: #{backup_file}"
    puts "Backing up: #{backup_path}"
    
    result = %x{tar -czf #{backup_file} #{backup_path}}
    
    if $?.success?
      puts "Backup created successfully: #{backup_file}"
      puts "Size: #{File.size(backup_file)} bytes"
    else
      puts "Backup failed with error: #{result}"
      exit 1
    end
  end
  
  desc "Generate backup with custom tar options"
  task :custom, [:name, :path, :options] => :environment do |t, args|
    backup_name = args[:name] || "backup_#{Time.now.strftime('%Y%m%d_%H%M%S')}"
    backup_path = args[:path] || "."
    tar_options = args[:options] || "-czf"
    
    backup_file = "#{backup_name}.tar.gz"
    
    puts "Creating backup: #{backup_file}"
    puts "Backing up: #{backup_path}"
    puts "Tar options: #{tar_options}"
    
    exec("tar #{tar_options} #{backup_file} #{backup_path}")
  end
  
  desc "Generate backup with exclude patterns"
  task :exclude, [:name, :path, :exclude_pattern] => :environment do |t, args|
    backup_name = args[:name] || "backup_#{Time.now.strftime('%Y%m%d_%H%M%S')}"
    backup_path = args[:path] || "."
    exclude = args[:exclude_pattern] || ""
    
    backup_file = "#{backup_name}.tar.gz"
    exclude_option = exclude.empty? ? "" : "--exclude='#{exclude}'"
    
    puts "Creating backup: #{backup_file}"
    puts "Backing up: #{backup_path}"
    puts "Excluding: #{exclude}" unless exclude.empty?
    
    command = "tar -czf #{backup_file} #{exclude_option} #{backup_path}"
    result = %x{#{command}}
    
    if $?.success?
      puts "Backup created successfully: #{backup_file}"
    else
      puts "Backup failed"
    end
  end
  
  desc "Generate incremental backup"
  task :incremental, [:name, :path, :snapshot_file] => :environment do |t, args|
    backup_name = args[:name] || "backup_#{Time.now.strftime('%Y%m%d_%H%M%S')}"
    backup_path = args[:path] || "."
    snapshot = args[:snapshot_file] || "backup.snapshot"
    
    backup_file = "#{backup_name}.tar.gz"
    
    puts "Creating incremental backup: #{backup_file}"
    puts "Backing up: #{backup_path}"
    puts "Using snapshot: #{snapshot}"
    
    %x{tar -czf #{backup_file} --listed-incremental=#{snapshot} #{backup_path}}
    
    if $?.success?
      puts "Incremental backup created successfully: #{backup_file}"
    else
      puts "Incremental backup failed"
    end
  end
  
  desc "Generate backup with verbose output"
  task :verbose, [:name, :path] => :environment do |t, args|
    backup_name = args[:name] || "backup_#{Time.now.strftime('%Y%m%d_%H%M%S')}"
    backup_path = args[:path] || "."
    
    backup_file = "#{backup_name}.tar.gz"
    
    puts "Creating backup: #{backup_file}"
    puts "Backing up: #{backup_path}"
    
    exec("tar -czvf #{backup_file} #{backup_path}")
  end
end