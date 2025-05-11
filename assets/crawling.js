// ==UserScript==
// @name         Udemy Transcript Collector (per section)
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Collect transcripts from Udemy courses
// @author       Hayes
// @match        https://www.udemy.com/course/*
// @grant        GM_registerMenuCommand
// ==/UserScript==

(function() {
    'use strict';

    // Configuration object containing all constants and settings
    const CONFIG = {
        WS_URL: "ws://localhost:8765",
        SELECTORS: {
            transcript: "button[data-purpose='transcript-toggle']",
            sections: "div[data-purpose='curriculum-section-container'] div[data-purpose^='section-panel']",
            lectures: "li[class^='curriculum-item-link--curriculum-item--']",
            nextButton: '#go-to-next-item',
            transcriptText: "span[data-purpose='cue-text']",
            sectionTitle: ".ud-accordion-panel-title",
            lectureTitle: "span[data-purpose='item-title']"
        },
        TIMEOUTS: {
            wsConnect: 5000,
            elementWait: 2000,
            transcriptWait: 3000,
            lectureWait: 7000,
            typescriptTextWait: 10000,
            responseWait: 5000
        }
    };

    // WebSocket client class for handling communication with the server
    class WebSocketClient {
        constructor(url, maxRetries = 3) {
            this.url = url;
            this.maxRetries = maxRetries;
            this.socket = null;
        }

        async connect() {
            let retries = 0;

            const tryConnect = () => {
                return new Promise((resolve, reject) => {
                    const ws = new WebSocket(this.url);
                    const timeout = setTimeout(() => {
                        ws.close();
                        retry();
                    }, CONFIG.TIMEOUTS.wsConnect);

                    ws.onopen = () => {
                        console.log(`✅ Connected to WebSocket server`);
                        clearTimeout(timeout);
                        this.socket = ws;
                        resolve(ws);
                    };

                    ws.onerror = (error) => {
                        console.log(`❌ WebSocket Error (attempt ${retries + 1}/${this.maxRetries}):`, error);
                        clearTimeout(timeout);
                        retry();
                    };

                    const retry = () => {
                        if (retries < this.maxRetries) {
                            retries++;
                            console.log(`🔄 Retrying connection... (${retries}/${this.maxRetries})`);
                            setTimeout(() => tryConnect().then(resolve).catch(reject), 1000 * retries);
                        } else {
                            reject(new Error('Failed to connect to WebSocket server'));
                        }
                    };
                });
            };

            return tryConnect();
        }

        isHealthy() {
            return this.socket && this.socket.readyState === WebSocket.OPEN;
        }

        async sendWithResponse(data, timeout = CONFIG.TIMEOUTS.responseWait) {
            if (!this.isHealthy()) {
                throw new Error('WebSocket connection is not open');
            }

            return new Promise((resolve, reject) => {
                const messageId = Date.now().toString();
                const dataToSend = { ...data, messageId };

                const timeoutId = setTimeout(() => {
                    cleanup();
                    reject(new Error('Socket response timeout'));
                }, timeout);

                const handleMessage = (event) => {
                    let response;
                    try {
                        response = JSON.parse(event.data);
                    } catch (e) {
                        response = event.data;
                    }

                    if (response.messageId === messageId) {
                        cleanup();
                        resolve(response);
                    }
                };

                const cleanup = () => {
                    clearTimeout(timeoutId);
                    this.socket.removeEventListener('message', handleMessage);
                };

                this.socket.addEventListener('message', handleMessage);
                this.socket.send(JSON.stringify(dataToSend));
            });
        }

        close() {
            if (this.socket) {
                this.socket.close();
            }
        }
    }

    // Helper class for DOM manipulation and element waiting
    class DOMHelper {
        static async waitForElements(selector, options = {}) {
            const {
                buttonElement = null,
                timeout = CONFIG.TIMEOUTS.elementWait,
                parent = document,
                condition = null
            } = options;

            return new Promise((resolve, reject) => {
                let timeoutId;
                let observer;

                const cleanup = () => {
                    if (timeoutId) clearTimeout(timeoutId);
                    if (observer) observer.disconnect();
                };

                const checkElements = () => {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0 && (!condition || condition(elements))) {
                        return elements;
                    }
                    return null;
                };

                const observe = () => {
                    const element = checkElements();
                    if (element) {
                        cleanup();
                        resolve(element);
                        return;
                    }

                    observer = new MutationObserver(() => {
                        const element = checkElements();
                        if (element) {
                            cleanup();
                            resolve(element);
                        }
                    });

                    observer.observe(parent, {
                        childList: true,
                        subtree: true,
                        attributes: true
                    });

                    timeoutId = setTimeout(() => {
                        cleanup();
                        reject(new Error(`Element not found within ${timeout}ms (selector: ${selector})`));
                    }, timeout);
                };

                if (buttonElement) {
                    try {
                        buttonElement.click();
                        observe();
                    } catch (error) {
                        cleanup();
                        reject(new Error(`Failed to click button: ${error.message}`));
                    }
                } else {
                    observe();
                }
            });
        }
    }

    // Main class for collecting transcripts
    class TranscriptCollector {
        constructor(wsClient) {
            this.wsClient = wsClient;
        }

        async getSectionsList() {
            const sections = document.querySelectorAll(CONFIG.SELECTORS.sections);
            return Array.from(sections).map((section, index) => {
                const title = section.querySelector(CONFIG.SELECTORS.sectionTitle)?.innerText.trim() || "Unknown Section";
                return { index, title };
            });
        }

        async expandSection(section) {
            const toggleButton = section.querySelector("button.ud-btn.js-panel-toggler");
            if (toggleButton && toggleButton.getAttribute("aria-expanded") === "false") {
                await DOMHelper.waitForElements(CONFIG.SELECTORS.sections, {
                    buttonElement: toggleButton,
                    condition: _ => toggleButton.getAttribute("aria-expanded") === "true",
                });
            }
        }

        async collectTranscriptsForSection(sectionIndex) {
            const sections = document.querySelectorAll(CONFIG.SELECTORS.sections);
            if (sectionIndex >= sections.length) {
                throw new Error('Invalid section index');
            }

            const section = sections[sectionIndex];
            await this.expandSection(section);

            const sectionTitle = section.querySelector(CONFIG.SELECTORS.sectionTitle)?.innerText.trim() || "Unknown Section";
            console.log(`📂 Processing section: ${sectionTitle}`);

            const lectures = section.querySelectorAll(CONFIG.SELECTORS.lectures);
            let currentLecture = document.querySelector('li[aria-current="true"]');
            let startProcessing = false;

            const lectureArray = Array.from(lectures);
            if (lectureArray.includes(currentLecture)) {
                startProcessing = true;
            }

            for (const [i, lecture] of lectureArray.entries()) {
                if (!startProcessing && lecture !== currentLecture) {
                    continue;
                }
                startProcessing = true;

                await this.processLecture(lecture, section, sectionTitle, 0, i);

                const nextLecture = lectureArray[i + 1];
                if (!nextLecture) {
                    console.log(`✅ Section ${sectionTitle} completed`);
                    break;
                }

                await this.navigateToNextLecture();
                await this.expandSection(section);
            }
        }

        async processLecture(lecture, section, sectionTitle, offset, index) {
            const lectureTitle = lecture.querySelector(CONFIG.SELECTORS.lectureTitle)?.innerText.trim() || "Unknown Lecture";

            try {
                let transcriptButtons = await DOMHelper.waitForElements(CONFIG.SELECTORS.transcript, {
                    timeout: CONFIG.TIMEOUTS.transcriptWait
                });

                if (transcriptButtons.length === 0) {
                    console.log(`⚠️ No transcript found for: ${lectureTitle}, skipping...`);
                    return;
                }

                console.log(`🔎 Found transcript button for: ${lectureTitle}`);

                await DOMHelper.waitForElements(CONFIG.SELECTORS.transcriptText, {
                    buttonElement: transcriptButtons[0],
                    timeout: CONFIG.TIMEOUTS.typescriptTextWait
                });

                const transcriptTexts = [...document.querySelectorAll(CONFIG.SELECTORS.transcriptText)]
                    .map(el => el.innerText.trim())
                    .filter(text => text.length > 0);

                console.log(`✅ Transcript found for: ${lectureTitle}`);

                if (transcriptTexts.length === 0) {
                    console.log(`⚠️ No transcript available for: ${lectureTitle}, skipping...`);
                    return;
                }

                await this.wsClient.sendWithResponse({
                    action: "save_transcript",
                    section: sectionTitle,
                    title: lectureTitle,
                    transcripts: transcriptTexts
                });

                console.log(`📤 Sent data for: ${lectureTitle}`);

                await DOMHelper.waitForElements(CONFIG.SELECTORS.lectures, {
                    buttonElement: transcriptButtons[0],
                    condition: el => el[index].getAttribute("aria-current") === "true"
                });
            } catch (error) {
                console.log(`⚠️ Error processing lecture ${lectureTitle}:`, error.message);
            }
        }

        async navigateToNextLecture() {
            let nextButton = document.querySelector(CONFIG.SELECTORS.nextButton);
            if (!nextButton) {
                throw new Error('Next lecture button not found');
            }

            try {
                await DOMHelper.waitForElements(CONFIG.SELECTORS.nextButton, {
                    buttonElement: nextButton,
                    condition: el => el[0] !== nextButton,
                    timeout: CONFIG.TIMEOUTS.lectureWait
                });
            } catch (error) {
                console.log(`⚠️ Error navigating to the next lecture:`, error.message);
                throw error;
            }
        }
    }

    // Main execution function
    async function main() {
        const wsClient = new WebSocketClient(CONFIG.WS_URL);
        try {
            await wsClient.connect();
            const collector = new TranscriptCollector(wsClient);

            // Get current section index
            const currentLecture = document.querySelector('li[aria-current="true"]');
            let currentSectionIndex = 0;

            if (currentLecture) {
                const sections = document.querySelectorAll(CONFIG.SELECTORS.sections);
                for (let i = 0; i < sections.length; i++) {
                    if (sections[i].contains(currentLecture)) {
                        currentSectionIndex = i;
                        break;
                    }
                }
            }

            // Process current section
            await collector.collectTranscriptsForSection(currentSectionIndex);

        } catch (error) {
            console.error('❌ Fatal error:', error);
        } finally {
            wsClient.close();
        }
    }

    // Register Tampermonkey menu command
    GM_registerMenuCommand("Collect Current Section Transcripts", main, "t");
})();