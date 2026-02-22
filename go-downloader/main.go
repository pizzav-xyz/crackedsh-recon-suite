package main

import (
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"sync"
)

func main() {
	if len(os.Args) != 2 {
		fmt.Fprintf(os.Stderr, "Usage: %s <input_file>\n", os.Args[0])
		os.Exit(1)
	}

	inputFile := os.Args[1]

	// Read the input file
	content, err := os.ReadFile(inputFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file %s: %v\n", inputFile, err)
		os.Exit(1)
	}

	// Compile regex to extract download URLs
	re := regexp.MustCompile(`'download_url':\s*'([^']+)`)
	matches := re.FindAllStringSubmatch(string(content), -1)

	// Limit concurrent downloads with a semaphore (aria2 handles its own threading internally)
	const maxConcurrentDownloads = 5 // Lower number since aria2 already uses multiple connections
	semaphore := make(chan struct{}, maxConcurrentDownloads)

	var wg sync.WaitGroup
	counter := 1

	for _, match := range matches {
		if len(match) > 1 {
			url := match[1]

			// Skip if URL is "None"
			if url != "None" {
				wg.Add(1)
				go func(u string, c int) {
					defer wg.Done()
					semaphore <- struct{}{}        // Acquire
					defer func() { <-semaphore }() // Release

					filename := fmt.Sprintf("%d.txt", c)
					fmt.Printf("Downloading %s -> %s\n", u, filename)

					err := downloadWithAria2(u, filename)
					if err != nil {
						fmt.Fprintf(os.Stderr, "Error downloading %s: %v\n", u, err)
					}
				}(url, counter)
				counter++
			}
		}
	}

	// Wait for all downloads to complete
	wg.Wait()
	fmt.Println("All downloads completed.")
}

func downloadWithAria2(url, filename string) error {
	// Use aria2c with 4 connections per file for better performance
	cmd := exec.Command("aria2c", "--max-connection-per-server=4", "--split=4", "--continue=true", "-o", filename, url)

	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("aria2c failed: %v, output: %s", err, string(output))
	}

	return nil
}
