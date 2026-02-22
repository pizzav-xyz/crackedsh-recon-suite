package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"regexp"
)

func main() {
	if len(os.Args) != 2 {
		fmt.Fprintf(os.Stderr, "Usage: %s <input_file>\n", os.Args[0])
		os.Exit(1)
	}

	inputFile := os.Args[1]
	counter := 1

	// Read the input file
	content, err := os.ReadFile(inputFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file %s: %v\n", inputFile, err)
		os.Exit(1)
	}

	// Compile regex to extract download URLs
	re := regexp.MustCompile(`'download_url':\s*'([^']+)`)
	matches := re.FindAllStringSubmatch(string(content), -1)

	for _, match := range matches {
		if len(match) > 1 {
			url := match[1]

			// Skip if URL is "None"
			if url != "None" {
				fmt.Printf("Downloading %s -> %d.txt\n", url, counter)

				err := downloadFile(url, fmt.Sprintf("%d.txt", counter))
				if err != nil {
					fmt.Fprintf(os.Stderr, "Error downloading %s: %v\n", url, err)
				}

				counter++
			}
		}
	}
}

func downloadFile(url, filename string) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// Check for successful response
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, resp.Status)
	}

	out, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	return err
}
