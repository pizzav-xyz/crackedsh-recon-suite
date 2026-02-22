# Enhanced Go Downloader

This is an enhanced version of the concurrent file downloader with beautiful progress bars and improved UI elements.

## Features

- **Concurrent Downloads**: Downloads multiple files simultaneously (up to 10 concurrent downloads by default)
- **Progress Bars**: Visual progress indicators for each download with percentage completion
- **Speed Monitoring**: Shows download speed for each file
- **ETA Display**: Estimated time of arrival for each download
- **Colorful Output**: Beautiful terminal UI with decorated progress bars
- **Error Handling**: Graceful handling of download errors
- **Summary Report**: Shows download summary upon completion

## Libraries Used

- `github.com/vbauerster/mpb/v8` - Multi Progress Bar library for terminal applications
- `github.com/vbauerster/mpb/v8/decor` - Decorations for progress bars (percentages, speeds, ETA)

## Usage

```bash
./go-downloader-enhanced <input_file>
```

Where `<input_file>` contains JSON-like content with `'download_url': 'URL'` patterns to extract and download.

## How it Works

1. Reads an input file containing multiple `'download_url': 'URL'` patterns
2. Extracts all URLs using regex
3. Creates concurrent download workers with a semaphore limiting the number of simultaneous downloads
4. Shows individual progress bars for each download with speed and ETA
5. Reports summary when all downloads are complete

## Performance

- Downloads now run concurrently with progress tracking
- Visual feedback shows all active downloads simultaneously
- Much faster than the original sequential version
- Resource-friendly limits on concurrent connections