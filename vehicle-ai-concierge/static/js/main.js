// static/js/main.js
const mainContainer = document.getElementById('main-container');
const chatInput = document.getElementById('chat-input');
const initialContent = document.getElementById('initial-content');
const suggestionsContainer = document.getElementById('suggestions-container');
const chatResults = document.getElementById('chat-results');
const sendButton = document.getElementById('send-button');
const micButton = document.getElementById('mic-button');
const chatContainerWrapper = document.getElementById('chat-container-wrapper');
const footerChat = document.getElementById('footer-chat');
const uploadButton = document.getElementById('upload-button');
const fileUpload = document.getElementById('file-upload');
const suggestionItems = document.querySelectorAll('.suggestion-item');

// Elements for the side panel
const sidePanel = document.getElementById('side-panel');
const sidePanelContent = document.getElementById('side-panel-content');
const closePanelButton = document.getElementById('close-panel-button');
const overlay = document.getElementById('overlay');

// Elements for the image modal
const imageModal = document.getElementById('image-modal');
const modalImage = document.getElementById('modal-image');
const closeModalButton = document.getElementById('close-modal-button');
const imageEditPrompt = document.getElementById('image-edit-prompt');
const editImageButton = document.getElementById('edit-image-button');


let isChatActive = false;
let isAudioActive = false;
let userId = "111"; // Example user ID

// Store rich content data globally
window.searchResultsStore = {};
window.dealershipsStore = {}; 
window.accessoriesStore = {};
window.leadStore = {};

const activateChat = () => {
    if (isChatActive) return;
    isChatActive = true;
    
    chatResults.classList.add('flex-grow');
    chatInput.classList.remove('initial-input-height');
    mainContainer.classList.remove('justify-center');
    mainContainer.classList.add('justify-between');

    initialContent.style.maxHeight = '0';
    initialContent.style.opacity = '0';
    initialContent.style.margin = '0';
    initialContent.style.padding = '0';
    initialContent.style.visibility = 'hidden';
    
    suggestionsContainer.style.maxHeight = '0';
    suggestionsContainer.style.opacity = '0';
    suggestionsContainer.style.marginTop = '0';
    suggestionsContainer.style.padding = '0';
    suggestionsContainer.style.visibility = 'hidden';

    chatResults.style.opacity = '1';
    chatResults.style.height = 'auto';
    
    chatContainerWrapper.classList.add('pt-4', 'border-t', 'border-gray-200');
    footerChat.classList.remove('hidden');
};

const toggleAudioMode = () => {
    isAudioActive = !isAudioActive;
    micButton.classList.toggle('mic-active', isAudioActive);

    if (isAudioActive) {
        chatInput.contentEditable = 'false';
        chatInput.innerHTML = '';
        chatInput.dataset.oldPlaceholder = chatInput.getAttribute('placeholder');
        chatInput.setAttribute('placeholder', 'Listening... Speak now.');
    } else {
        chatInput.contentEditable = 'true';
        chatInput.setAttribute('placeholder', chatInput.dataset.oldPlaceholder || 'Ask anything...');
    }
};

const displayUserMessage = (message) => {
    const userQueryDiv = document.createElement('div');
    userQueryDiv.className = 'flex justify-end mb-4 animate-fade-in';
    userQueryDiv.innerHTML = `
        <div class="bg-blue-600 text-white py-2 px-4 rounded-2xl max-w-lg">
            <p class="text-base whitespace-pre-wrap">${message}</p>
        </div>
    `;
    chatResults.appendChild(userQueryDiv);
    chatResults.scrollTop = chatResults.scrollHeight;
};

// Helper function to convert snake_case to Title Case for display labels
const toTitleCase = (str) => {
    return str.replace(/_/g, ' ')
              .replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
};


const displayAgentResponse = (response) => {
    const agentResponseDiv = document.createElement('div');
    agentResponseDiv.className = 'mb-6 animate-fade-in';
    
    let richContentHtml = '';
    let displayText = response.text;

    // UI Cleanup: If the text looks like raw JSON, show a generic message.
    if (displayText && (displayText.trim().startsWith('```json') || (displayText.trim().startsWith('{') && displayText.trim().endsWith('}')))) {
        displayText = "I've found some information for you. Please see the options below.";
    }


    if (response.rich_content && response.rich_content.length > 0) {
        const firstItem = response.rich_content[0];

        // Case 1: Website Search Results
        if (firstItem.snippet !== undefined && firstItem.link !== undefined) {
            const resultsId = `results-${Date.now()}`;
            window.searchResultsStore[resultsId] = response.rich_content;
            
            const hasImages = response.rich_content.some(item => item.image);
            if (hasImages) {
                let galleryHtml = '<div class="mt-4 image-gallery-container">';
                response.rich_content.forEach(item => {
                    if (item.image) {
                        galleryHtml += `
                            <div class="image-gallery-item" data-full-src="${item.image}">
                                <img src="${item.image}" alt="${item.title}">
                            </div>
                        `;
                    }
                });
                galleryHtml += '</div>';
                richContentHtml += galleryHtml;
            }

            richContentHtml += `
                <div class="mt-4">
                    <button class="search-results-pill inline-flex items-center bg-transparent border-2 border-red-500 text-red-600 rounded-full px-4 py-1 text-sm font-semibold cursor-pointer hover:bg-red-50 transition-colors" data-results-id="${resultsId}">
                        View All Search Results
                    </button>
                </div>
            `;
        }
        // Case 2: Dealership Results
        else if (firstItem.address && firstItem.phone) {
            let dealerCardsHtml = '<div class="mt-4 flex flex-col gap-3">';
            response.rich_content.forEach(dealer => {
                window.dealershipsStore[dealer.id] = dealer;
                dealerCardsHtml += `
                    <button class="clickable-card dealer-chip-card" data-dealer-id="${dealer.id}">
                        <div class="dealer-name">${dealer.name}</div>
                        <div class="dealer-address">${dealer.address}</div>
                        <div class="dealer-phone">${dealer.phone}</div>
                    </button>
                `;
            });
            dealerCardsHtml += '</div>';
            richContentHtml = dealerCardsHtml;
        }
        // Case 3: Accessory/Part Results
        else if (firstItem.part_number && firstItem.price) {
             let accessoryCardsHtml = '<div class="mt-4 flex flex-col gap-3">';
            response.rich_content.forEach(part => {
                window.accessoriesStore[part.id] = part;
                accessoryCardsHtml += `
                    <button class="clickable-card accessory-chip-card" data-accessory-id="${part.id}">
                        <span class="accessory-name">${part.name}</span>
                        <span class="accessory-price">$${part.price.toFixed(2)}</span>
                    </button>
                `;
            });
            accessoryCardsHtml += '</div>';
            richContentHtml = accessoryCardsHtml;
        }
        // Case 4: Lead Generation Confirmation
        else if (firstItem.first_name && firstItem.vehicle_model) {
            const leadData = firstItem;
            const leadId = `lead-${Date.now()}`;
            window.leadStore[leadId] = leadData; 

            let detailsHtml = '';
            const displayOrder = [
                'first_name', 'last_name', 'vehicle_model', 'vehicle_year', 
                'email', 'phone_number', 'zip_code', 'contact_preference'
            ];

            displayOrder.forEach(key => {
                if (leadData[key] && key !== 'dealer_summary' && key !== 'notes') { // Exclude notes from main card
                    detailsHtml += `<p><strong>${toTitleCase(key)}:</strong> ${leadData[key]}</p>`;
                }
            });

            let summaryPillHtml = '';
            if (leadData.dealer_summary || leadData.notes) {
                summaryPillHtml = `
                    <div class="mt-4">
                         <button class="dealer-summary-pill inline-flex items-center bg-gray-200 text-gray-700 rounded-full px-4 py-1 text-sm font-semibold cursor-pointer hover:bg-gray-300 transition-colors" data-lead-id="${leadId}">
                            View Notes for Dealer
                        </button>
                    </div>
                `;
            }

            richContentHtml = `
                <div class="mt-4 lead-confirmation-card">
                    <h3 class="font-bold text-lg mb-3 text-gray-900">Please Confirm Your Information</h3>
                    <div class="lead-details">
                        ${detailsHtml}
                    </div>
                    <div class="mt-4">
                        <button class="w-full bg-blue-600 text-white rounded-lg px-4 py-2 font-semibold hover:bg-blue-700 transition-colors">Looks Good, Get My Quote!</button>
                    </div>
                </div>
                ${summaryPillHtml}
            `;
        }
        // Case 5: Edited Image
        else if (firstItem.image_url) {
            richContentHtml = `<div class="edited-image-card mt-4"><img src="${firstItem.image_url}" alt="Edited vehicle image"></div>`;
        }
    }
    
    const formattedText = displayText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');

    agentResponseDiv.innerHTML = `
        <div class="prose max-w-none text-base text-gray-700">${formattedText}</div>
        ${richContentHtml}
    `;
    chatResults.appendChild(agentResponseDiv);
    chatResults.scrollTop = chatResults.scrollHeight;
};

const processQuery = async (queryOverride = null) => {
    const query = queryOverride || chatInput.innerText.trim();
    if (query === '') return;

    if (!isChatActive) activateChat();
    displayUserMessage(query);
    chatInput.innerHTML = '';

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'mb-6';
    loadingDiv.innerHTML = `<div class="text-gray-500">Thinking...</div>`;
    chatResults.appendChild(loadingDiv);
    chatResults.scrollTop = chatResults.scrollHeight;

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, message: query }),
        });

        chatResults.removeChild(loadingDiv); 

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const data = await response.json();
        displayAgentResponse(data);

    } catch (error) {
        console.error('Error fetching chat response:', error);
        chatResults.removeChild(loadingDiv);
        displayAgentResponse({ text: "Sorry, I encountered an error. Please try again." });
    }
};

const openSidePanelWithContent = (title, content) => {
    document.querySelector('#side-panel h2').innerHTML = `<span class="material-icons mr-2">${title.icon}</span> ${title.text}`;
    sidePanelContent.innerHTML = content;
    overlay.classList.remove('hidden');
    sidePanel.classList.remove('translate-x-full');
};

const openSearchResultsPanel = (resultsId) => {
    const results = window.searchResultsStore[resultsId];
    if (!results) return;

    let content = '<div class="space-y-4">';
    results.forEach(item => {
        let imageHtml = '';
        if (item.image) {
            imageHtml = `<img src="${item.image}" alt="${item.title}" class="w-full h-auto rounded-lg mb-2 object-cover">`;
        }
        content += `
            <div class="border-b pb-4 last:border-b-0">
                ${imageHtml}
                <a href="${item.link}" target="_blank" class="text-lg font-semibold text-blue-600 hover:underline">${item.title}</a>
                <p class="text-sm text-gray-600 mt-1">${item.snippet}</p>
                <a href="${item.link}" target="_blank" class="text-xs text-gray-500 truncate block mt-1 hover:text-blue-500">${item.link}</a>
            </div>`;
    });
    content += '</div>';
    
    openSidePanelWithContent({icon: 'search', text: 'Search Results'}, content);
};

const openDealerPanel = (dealerId) => {
    const dealer = window.dealershipsStore[dealerId];
    if (!dealer) return;

    let hoursHtml = '<ul class="text-sm text-gray-600">';
    for (const [day, hour] of Object.entries(dealer.hours)) {
        hoursHtml += `<li><span class="font-medium">${day}:</span> ${hour}</li>`;
    }
    hoursHtml += '</ul>';

    let inventoryHtml = '<div class="mt-4"><h4 class="font-semibold text-gray-700">Inventory Highlights</h4><ul class="list-disc list-inside text-sm text-gray-600">';
    dealer.inventory.forEach(inv => {
        inventoryHtml += `<li>${inv.count} x ${inv.model} ${inv.trim}</li>`;
    });
    inventoryHtml += '</ul></div>';

    const content = `
        <div class="space-y-4">
            <div>
                <h3 class="text-xl font-bold text-gray-800">${dealer.name}</h3>
                <p class="text-md text-gray-600">${dealer.address}</p>
                <p class="text-md text-gray-600">Phone: ${dealer.phone}</p>
                ${dealer.distance_miles ? `<p class="text-sm text-gray-500 mt-1">Approx. ${dealer.distance_miles.toFixed(1)} miles away</p>` : ''}
                <a href="[https://www.buick.com](https://www.buick.com)" target="_blank" class="text-blue-600 hover:underline mt-2 inline-block">Visit Website</a>
            </div>
            <div class="border-t pt-4">
                <h4 class="font-semibold text-gray-700">Hours</h4>
                ${hoursHtml}
            </div>
            <div class="border-t pt-4">
                ${inventoryHtml}
            </div>
        </div>
    `;

    openSidePanelWithContent({icon: 'store', text: 'Dealership Info'}, content);
};

const openAccessoryPanel = (accessoryId) => {
    const part = window.accessoriesStore[accessoryId];
    if (!part) return;

    let compatibilityHtml = '<ul class="list-disc list-inside text-sm text-gray-600">';
    part.compatibility.forEach(comp => {
        compatibilityHtml += `<li>${comp.model} (${comp.years.join(', ')})</li>`;
    });
    compatibilityHtml += '</ul>';

    const content = `
         <div class="space-y-4">
            <div>
                <h3 class="text-xl font-bold text-gray-800">${part.name}</h3>
                <p class="text-2xl font-bold text-blue-700 mt-1">$${part.price.toFixed(2)}</p>
                <p class="text-md text-gray-600 mt-2">${part.description}</p>
                <p class="text-sm text-gray-500 mt-2">Part Number: ${part.part_number}</p>
            </div>
            <div class="border-t pt-4">
                <h4 class="font-semibold text-gray-700">Compatibility</h4>
                ${compatibilityHtml}
            </div>
        </div>
    `;
     openSidePanelWithContent({icon: 'build', text: 'Accessory Details'}, content);
};

const openDealerSummaryPanel = (leadId) => {
    const lead = window.leadStore[leadId];
    if (!lead) return;
    
    const summaryText = lead.dealer_summary || lead.notes || "No additional notes were provided.";

    const content = `<p class="text-base text-gray-700 whitespace-pre-wrap">${summaryText}</p>`;
    openSidePanelWithContent({icon: 'description', text: 'Notes for Dealer'}, content);
};

// Functions to handle the image modal
const openImageModal = (src) => {
    modalImage.src = src;
    imageModal.classList.remove('hidden');
};

const closeImageModal = () => {
    imageModal.classList.add('hidden');
    modalImage.src = '';
    imageEditPrompt.value = ''; // Clear the prompt
};


const closeSidePanel = () => {
    overlay.classList.add('hidden');
    sidePanel.classList.add('translate-x-full');
};

// Event Listeners
micButton.addEventListener('click', toggleAudioMode);
uploadButton.addEventListener('click', () => fileUpload.click());
sendButton.addEventListener('click', () => processQuery());
closeModalButton.addEventListener('click', closeImageModal);
imageModal.addEventListener('click', (e) => { 
    if (e.target === imageModal) {
        closeImageModal();
    }
});

// NEW: Event listener for the image edit button
editImageButton.addEventListener('click', () => {
    const imageUrl = modalImage.src;
    const prompt = imageEditPrompt.value.trim();
    if (!imageUrl || !prompt) {
        alert("Please enter an edit instruction.");
        return;
    }
    const fullQuery = `Edit this image: ${imageUrl} with this prompt: ${prompt}`;
    closeImageModal();
    processQuery(fullQuery);
});


chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault(); 
        processQuery();
    }
});

suggestionItems.forEach(item => {
    item.addEventListener('click', () => {
        const suggestionText = item.querySelector('p').innerText;
        chatInput.innerText = suggestionText;
        setTimeout(processQuery, 0);
    });
});

closePanelButton.addEventListener('click', closeSidePanel);
overlay.addEventListener('click', closeSidePanel);

// Use event delegation for dynamically created rich content
chatResults.addEventListener('click', (e) => {
    const searchPill = e.target.closest('.search-results-pill');
    if (searchPill) {
        openSearchResultsPanel(searchPill.dataset.resultsId);
        return;
    }

    const dealerCard = e.target.closest('.dealer-chip-card');
    if (dealerCard) {
        openDealerPanel(dealerCard.dataset.dealerId);
        return;
    }

    const accessoryCard = e.target.closest('.accessory-chip-card');
    if (accessoryCard) {
        openAccessoryPanel(accessoryCard.dataset.accessoryId);
        return;
    }

    const summaryPill = e.target.closest('.dealer-summary-pill');
    if (summaryPill) {
        openDealerSummaryPanel(summaryPill.dataset.leadId);
        return;
    }

    const galleryItem = e.target.closest('.image-gallery-item');
    if (galleryItem) {
        openImageModal(galleryItem.dataset.fullSrc);
        return;
    }
});
