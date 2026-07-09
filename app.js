// 設定項目
        const apiProviderSelect = document.getElementById('api-provider');
        const apiKeyInput = document.getElementById('api-key');
        const toggleApiKeyBtn = document.getElementById('toggle-api-key');
        if (toggleApiKeyBtn && apiKeyInput) {
            toggleApiKeyBtn.addEventListener('click', () => {
                const isPassword = apiKeyInput.type === 'password';
                apiKeyInput.type = isPassword ? 'text' : 'password';
                toggleApiKeyBtn.textContent = isPassword ? '🙈' : '👁️';
            });
        }
        const apiKeyGroup = document.getElementById('api-key-group');
        const apiUrlInput = document.getElementById('api-url');
        const apiUrlLabel = document.getElementById('api-url-label');
        const modelSelect = document.getElementById('model-select');
        const modelCustomInput = document.getElementById('model-custom');
        const searchToggle = document.getElementById('web-search-toggle');
        const historyRagToggle = document.getElementById('history-rag-toggle');
        const agentModeToggle = document.getElementById('agent-mode-toggle');
        const systemPromptInput = document.getElementById('system-prompt');
        const tempInput = document.getElementById('temperature');
        const maxTokensInput = document.getElementById('max-tokens');
        const clearBtn = document.getElementById('clear-btn');
        const statusIndicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        const headerModelName = document.getElementById('header-model-name');
        
        // チャット項目
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        const messageList = document.getElementById('message-list');
        const attachBtn = document.getElementById('attach-btn');
        const fileInput = document.getElementById('file-input');
        const previewContainer = document.getElementById('preview-container');

        // 生成中断用の制御変数
        let currentAbortController = null;
        let isCancelled = false;

        // 添付ファイルを保持する配列
        let attachedFiles = [];
        // PDF.jsのワーカー設定
        if (window.pdfjsLib) {
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';
        }

        // 会話履歴を保持する配列
        let conversationHistory = [];
        let currentThreadId = 'thread-' + Date.now() + '-' + Math.random().toString(36).substring(2, 9);

        // AIプロバイダプリセット
        const PROVIDER_PRESETS = {
            colab: {
                url: '',
                label: 'Cloudflare API URL',
                placeholder: 'https://xxxx.trycloudflare.com',
                requiresKey: false,
                models: [{ value: 'auto', text: '接続後に自動検知' }]
            },
            openai: {
                url: 'https://api.openai.com/v1',
                label: 'API URL (OpenAI規格)',
                placeholder: 'https://api.openai.com/v1',
                requiresKey: true,
                models: [
                    { value: 'gpt-5.5', text: 'gpt-5.5 (次世代フラグシップ)' },
                    { value: 'gpt-4o', text: 'gpt-4o (標準モデル)' },
                    { value: 'gpt-4o-mini', text: 'gpt-4o-mini (軽量高速)' },
                    { value: 'custom', text: '手動入力...' }
                ]
            },
            gemini: {
                url: 'https://generativelanguage.googleapis.com/v1beta/openai',
                label: 'API URL (Gemini-OpenAI規格)',
                placeholder: 'https://generativelanguage.googleapis.com/v1beta/openai',
                requiresKey: true,
                models: [
                    { value: 'gemini-3.5-flash', text: 'gemini-3.5-flash (最新・高速)' },
                    { value: 'gemini-1.5-pro', text: 'gemini-1.5-pro (高性能)' },
                    { value: 'gemini-1.5-flash', text: 'gemini-1.5-flash (高速・安価)' },
                    { value: 'custom', text: '手動入力...' }
                ]
            },
            claude: {
                url: 'https://api.anthropic.com',
                label: 'API URL (Claude公式)',
                placeholder: 'https://api.anthropic.com',
                requiresKey: true,
                models: [
                    { value: 'claude-3-5-sonnet-20240620', text: 'claude-3.5-sonnet' },
                    { value: 'claude-3-opus-20240229', text: 'claude-3-opus' },
                    { value: 'claude-3-haiku-20240307', text: 'claude-3-haiku' },
                    { value: 'custom', text: '手動入力...' }
                ]
            },
            deepseek: {
                url: 'https://api.deepseek.com/v1',
                label: 'API URL (DeepSeek公式)',
                placeholder: 'https://api.deepseek.com/v1',
                requiresKey: true,
                models: [
                    { value: 'deepseek-chat', text: 'deepseek-chat (会話)' },
                    { value: 'deepseek-coder', text: 'deepseek-coder (コーディング)' },
                    { value: 'custom', text: '手動入力...' }
                ]
            },
            groq: {
                url: 'https://api.groq.com/openai/v1',
                label: 'API URL (Groq公式)',
                placeholder: 'https://api.groq.com/openai/v1',
                requiresKey: true,
                models: [
                    { value: 'llama-3.1-70b-versatile', text: 'llama-3.1-70b' },
                    { value: 'llama-3.1-8b-instant', text: 'llama-3.1-8b' },
                    { value: 'mixtral-8x7b-32768', text: 'mixtral-8x7b' },
                    { value: 'custom', text: '手動入力...' }
                ]
            },
            grok: {
                url: 'https://api.x.ai/v1',
                label: 'API URL (xAI Grok公式)',
                placeholder: 'https://api.x.ai/v1',
                requiresKey: true,
                models: [
                    { value: 'grok-2-1212', text: 'grok-2 (高性能モデル)' },
                    { value: 'grok-2-mini-1212', text: 'grok-2-mini (高速・軽量)' },
                    { value: 'grok-beta', text: 'grok-beta (ベータ版)' },
                    { value: 'custom', text: '手動入力...' }
                ]
            },
            openrouter: {
                url: 'https://openrouter.ai/api/v1',
                label: 'API URL (OpenRouter公式)',
                placeholder: 'https://openrouter.ai/api/v1',
                requiresKey: true,
                models: [
                    { value: 'anthropic/claude-3.5-sonnet', text: 'Claude 3.5 Sonnet' },
                    { value: 'google/gemini-flash-1.5', text: 'Gemini 1.5 Flash' },
                    { value: 'meta-llama/llama-3-70b-instruct', text: 'Llama 3 70B' },
                    { value: 'custom', text: '手動入力...' }
                ]
            },
            custom: {
                url: '',
                label: 'API Base URL',
                placeholder: 'https://your-custom-endpoint/v1',
                requiresKey: true,
                models: [
                    { value: 'custom', text: '手動入力...' }
                ]
            }
        };

        function updateProviderUI(provider) {
            const preset = PROVIDER_PRESETS[provider];
            if (!preset) return;

            apiUrlLabel.textContent = preset.label;
            apiUrlInput.placeholder = preset.placeholder;

            if (preset.requiresKey) {
                apiKeyGroup.style.display = 'flex';
                const savedKey = localStorage.getItem(`api_key_${provider}`);
                apiKeyInput.value = savedKey || '';
            } else {
                apiKeyGroup.style.display = 'none';
                apiKeyInput.value = '';
            }

            if (preset.url) {
                apiUrlInput.value = preset.url;
            } else if (provider === 'colab') {
                apiUrlInput.value = localStorage.getItem('colab_chat_api_url') || '';
            } else if (provider === 'custom') {
                apiUrlInput.value = localStorage.getItem('custom_chat_api_url') || '';
            }

            modelSelect.innerHTML = '';
            preset.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.value;
                opt.textContent = m.text;
                modelSelect.appendChild(opt);
            });

            const savedModel = localStorage.getItem(`api_model_${provider}`);
            if (savedModel && preset.models.some(m => m.value === savedModel)) {
                modelSelect.value = savedModel;
            } else {
                modelSelect.value = preset.models[0].value;
            }

            handleModelSelectChange();
        }

        function handleModelSelectChange() {
            const provider = apiProviderSelect.value;
            const isCustom = modelSelect.value === 'custom';
            if (isCustom) {
                modelCustomInput.style.display = 'block';
                const savedCustomModel = localStorage.getItem(`api_model_custom_${provider}`);
                modelCustomInput.value = savedCustomModel || '';
            } else {
                modelCustomInput.style.display = 'none';
            }
            updateHeaderModelName();
        }

        function updateHeaderModelName() {
            const provider = apiProviderSelect.value;
            const isCustom = modelSelect.value === 'custom';
            const selectedModel = isCustom ? modelCustomInput.value : modelSelect.value;
            headerModelName.textContent = selectedModel || '未設定';
        }

        const skillsListContainer = document.getElementById('skills-list-container');
        let availableSkills = [];

        async function loadSkills() {
            try {
                const response = await fetch('/list-skills');
                if (!response.ok) throw new Error('Failed to load skills');
                availableSkills = await response.json();

                skillsListContainer.innerHTML = '';
                if (availableSkills.length === 0) {
                    skillsListContainer.innerHTML = '<div style="font-size: 0.8rem; color: var(--text-muted);">利用可能なスキルはありません</div>';
                    return;
                }

                const savedEnabledSkills = JSON.parse(localStorage.getItem('colab_chat_enabled_skills') || '[]');

                availableSkills.forEach(skill => {
                    const skillDiv = document.createElement('div');
                    skillDiv.className = 'switch-container';
                    skillDiv.style.margin = '0';
                    skillDiv.style.padding = '0';
                    skillDiv.style.border = 'none';
                    skillDiv.style.background = 'none';
                    skillDiv.style.display = 'flex';
                    skillDiv.style.alignItems = 'center';
                    skillDiv.style.justifyContent = 'space-between';

                    const labelSpan = document.createElement('span');
                    labelSpan.className = 'switch-label';
                    labelSpan.style.fontSize = '0.85rem';
                    labelSpan.title = skill.description;
                    labelSpan.textContent = `⚡ ${skill.name}`;

                    const switchLabel = document.createElement('label');
                    switchLabel.className = 'switch';
                    switchLabel.style.width = '34px';
                    switchLabel.style.height = '20px';

                    const input = document.createElement('input');
                    input.type = 'checkbox';
                    input.value = skill.id;
                    input.checked = savedEnabledSkills.includes(skill.id);

                    const slider = document.createElement('span');
                    slider.className = 'slider';
                    slider.style.borderRadius = '20px';

                    input.addEventListener('change', () => {
                        const currentEnabled = JSON.parse(localStorage.getItem('colab_chat_enabled_skills') || '[]');
                        if (input.checked) {
                            if (!currentEnabled.includes(skill.id)) {
                                currentEnabled.push(skill.id);
                            }
                        } else {
                            const idx = currentEnabled.indexOf(skill.id);
                            if (idx !== -1) {
                                currentEnabled.splice(idx, 1);
                            }
                        }
                        localStorage.setItem('colab_chat_enabled_skills', JSON.stringify(currentEnabled));
                    });

                    switchLabel.appendChild(input);
                    switchLabel.appendChild(slider);
                    skillDiv.appendChild(labelSpan);
                    skillDiv.appendChild(switchLabel);
                    skillsListContainer.appendChild(skillDiv);
                });
            } catch (err) {
                console.error(err);
                skillsListContainer.innerHTML = '<div style="font-size: 0.8rem; color: #ef4444;">スキルのロードに失敗しました</div>';
            }
        }

        // 送信・生成中UIの初期化とリセット
        function resetGeneratingUI() {
            const cancelBtn = document.getElementById('cancel-btn');
            if (cancelBtn) cancelBtn.style.display = 'none';
            if (sendBtn) sendBtn.disabled = false;
            currentAbortController = null;
        }

        // スキルのインストール機能のイベントハンドラ
        function setupSkillInstallUI() {
            const toggleInstallFormBtn = document.getElementById('toggle-install-form-btn');
            const installFormContainer = document.getElementById('install-form-container');
            const skillInstallUrl = document.getElementById('skill-install-url');
            const installSkillSubmitBtn = document.getElementById('install-skill-submit-btn');
            const installStatusMsg = document.getElementById('install-status-msg');

            if (!toggleInstallFormBtn || !installFormContainer) return;

            toggleInstallFormBtn.addEventListener('click', () => {
                const isHidden = installFormContainer.style.display === 'none';
                installFormContainer.style.display = isHidden ? 'flex' : 'none';
                toggleInstallFormBtn.querySelector('span').textContent = isHidden ? 'ー インポートフォームを閉じる' : '＋ GitHubからスキルをインポート';
            });

            installSkillSubmitBtn.addEventListener('click', async () => {
                const url = skillInstallUrl.value.trim();
                if (!url) {
                    alert('GitHubリポジトリのURLを入力してください。');
                    return;
                }

                installSkillSubmitBtn.disabled = true;
                installSkillSubmitBtn.textContent = '処理中...';
                installStatusMsg.style.display = 'block';
                installStatusMsg.style.color = 'var(--text-muted)';
                installStatusMsg.textContent = '⏳ インストールまたはアップデートを実行中...';

                try {
                    const response = await fetch('/install-skill', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url })
                    });

                    const result = await response.json();
                    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);

                    installStatusMsg.style.color = '#34d399';
                    installStatusMsg.textContent = `✅ 成功: ${result.message || 'インストール完了'}`;
                    skillInstallUrl.value = '';
                    
                    // スキル一覧を再ロード
                    await loadSkills();
                } catch (err) {
                    console.error(err);
                    installStatusMsg.style.color = '#f87171';
                    installStatusMsg.textContent = `❌ エラー: ${err.message}`;
                } finally {
                    installSkillSubmitBtn.disabled = false;
                    installSkillSubmitBtn.textContent = 'インストール / 更新';
                }
            });
        }

        // モバイルサイドバー（ドロワー）のトグル制御
        function setupMobileMenuUI() {
            const menuToggle = document.getElementById('menu-toggle');
            const sidebar = document.getElementById('sidebar');
            const sidebarOverlay = document.getElementById('sidebar-overlay');

            if (!menuToggle || !sidebar || !sidebarOverlay) return;

            function toggleSidebar() {
                const isOpen = sidebar.classList.toggle('open');
                sidebarOverlay.classList.toggle('active', isOpen);
            }

            function closeSidebar() {
                sidebar.classList.remove('open');
                sidebarOverlay.classList.remove('active');
            }

            menuToggle.addEventListener('click', toggleSidebar);
            sidebarOverlay.addEventListener('click', closeSidebar);

            // サイドバー内の項目が変更されたり、アクションが起きたときも自動で閉じる
            apiProviderSelect.addEventListener('change', closeSidebar);
            modelSelect.addEventListener('change', closeSidebar);
            document.getElementById('clear-btn').addEventListener('click', closeSidebar);
        }

        // コードブロックの右上に「💾 サーバーへ保存」ボタンを追加する
        function addSaveButtonsToCodeBlocks(containerDiv) {
            const preElements = containerDiv.querySelectorAll('pre');
            preElements.forEach((pre) => {
                if (pre.querySelector('.save-code-btn')) return;

                pre.style.position = 'relative';

                const saveBtn = document.createElement('button');
                saveBtn.type = 'button';
                saveBtn.className = 'save-code-btn';
                saveBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:12px; height:12px; margin-right: 4px; display:inline-block; vertical-align:middle; stroke: #f3f4f6;"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>
                    <span>保存</span>
                `;
                
                saveBtn.style.position = 'absolute';
                saveBtn.style.top = '8px';
                saveBtn.style.right = '8px';
                saveBtn.style.background = 'rgba(30, 41, 59, 0.85)';
                saveBtn.style.border = '1px solid rgba(255, 255, 255, 0.12)';
                saveBtn.style.borderRadius = '4px';
                saveBtn.style.color = '#f3f4f6';
                saveBtn.style.padding = '4px 8px';
                saveBtn.style.fontSize = '0.75rem';
                saveBtn.style.cursor = 'pointer';
                saveBtn.style.display = 'flex';
                saveBtn.style.alignItems = 'center';
                saveBtn.style.zIndex = '10';
                saveBtn.style.transition = 'all 0.2s';
                saveBtn.style.outline = 'none';

                saveBtn.addEventListener('mouseenter', () => {
                    saveBtn.style.background = '#4f46e5';
                    saveBtn.style.borderColor = '#6366f1';
                });
                saveBtn.addEventListener('mouseleave', () => {
                    saveBtn.style.background = 'rgba(30, 41, 59, 0.85)';
                    saveBtn.style.borderColor = 'rgba(255, 255, 255, 0.12)';
                });

                saveBtn.addEventListener('click', async () => {
                    const code = pre.querySelector('code').textContent;
                    
                    const filePath = prompt("保存先のファイル名（例: src/index.js または test.py）を入力してください。\n※サーバーの作業フォルダ内に保存されます。", "");
                    
                    if (filePath === null) return;
                    if (!filePath.trim()) {
                        alert("パスを入力してください。");
                        return;
                    }

                    saveBtn.disabled = true;
                    saveBtn.querySelector('span').textContent = '保存中...';

                    try {
                        const res = await fetch('/write-file', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                path: filePath.trim(),
                                content: code
                            })
                        });

                        const result = await res.json();
                        if (!res.ok) throw new Error(result.error || `HTTP ${res.status}`);

                        saveBtn.style.background = '#10b981';
                        saveBtn.style.borderColor = '#10b981';
                        saveBtn.querySelector('span').textContent = '✅ 保存完了!';
                        setTimeout(() => {
                            saveBtn.style.background = 'rgba(30, 41, 59, 0.85)';
                            saveBtn.style.borderColor = 'rgba(255, 255, 255, 0.12)';
                            saveBtn.querySelector('span').textContent = '保存';
                        }, 2500);

                    } catch (err) {
                        console.error(err);
                        alert(`保存に失敗しました: ${err.message}`);
                        saveBtn.querySelector('span').textContent = '保存';
                    } finally {
                        saveBtn.disabled = false;
                    }
                });

                pre.appendChild(saveBtn);
            });
        }

        // ページロード時の初期化
        window.addEventListener('load', () => {
            loadSkills();
            setupSkillInstallUI();
            setupMobileMenuUI();
            const savedProvider = localStorage.getItem('api_provider') || 'colab';
            apiProviderSelect.value = savedProvider;
            updateProviderUI(savedProvider);

            const savedSearch = localStorage.getItem('colab_chat_web_search');
            if (savedSearch === 'true') {
                searchToggle.checked = true;
            }
            const savedHistoryRag = localStorage.getItem('colab_chat_history_rag');
            if (savedHistoryRag === 'true') {
                historyRagToggle.checked = true;
            }
            const savedAgentMode = localStorage.getItem('colab_chat_agent_mode');
            if (savedAgentMode === 'true') {
                agentModeToggle.checked = true;
            }

            // トグル変更時の保存処理
            agentModeToggle.addEventListener('change', () => {
                localStorage.setItem('colab_chat_agent_mode', agentModeToggle.checked);
            });
            searchToggle.addEventListener('change', () => {
                localStorage.setItem('colab_chat_web_search', searchToggle.checked);
            });
            historyRagToggle.addEventListener('change', () => {
                localStorage.setItem('colab_chat_history_rag', historyRagToggle.checked);
            });

            // Colabの場合のみ、URLがあれば自動接続検証
            if (savedProvider === 'colab' && apiUrlInput.value) {
                checkConnection(apiUrlInput.value);
            }
        });

        // UIイベントリスナー
        apiProviderSelect.addEventListener('change', () => {
            const provider = apiProviderSelect.value;
            localStorage.setItem('api_provider', provider);
            updateProviderUI(provider);
        });

        const saveApiKey = () => {
            const provider = apiProviderSelect.value;
            localStorage.setItem(`api_key_${provider}`, apiKeyInput.value.trim());
        };
        apiKeyInput.addEventListener('input', saveApiKey);
        apiKeyInput.addEventListener('change', saveApiKey);
        apiKeyInput.addEventListener('blur', saveApiKey);

        apiUrlInput.addEventListener('input', () => {
            const provider = apiProviderSelect.value;
            if (provider === 'colab') {
                localStorage.setItem('colab_chat_api_url', apiUrlInput.value.trim());
            } else if (provider === 'custom') {
                localStorage.setItem('custom_chat_api_url', apiUrlInput.value.trim());
            }
        });

        modelSelect.addEventListener('change', () => {
            const provider = apiProviderSelect.value;
            localStorage.setItem(`api_model_${provider}`, modelSelect.value);
            handleModelSelectChange();
        });

        modelCustomInput.addEventListener('input', () => {
            const provider = apiProviderSelect.value;
            localStorage.setItem(`api_model_custom_${provider}`, modelCustomInput.value.trim());
            updateHeaderModelName();
        });

        searchToggle.addEventListener('change', () => {
            localStorage.setItem('colab_chat_web_search', searchToggle.checked);
        });

        historyRagToggle.addEventListener('change', () => {
            localStorage.setItem('colab_chat_history_rag', historyRagToggle.checked);
        });

        // 添付ボタンクリック
        attachBtn.addEventListener('click', () => {
            fileInput.click();
        });

        // ファイル選択イベント
        fileInput.addEventListener('change', (e) => {
            handleSelectedFiles(e.target.files);
            fileInput.value = ''; // リセットして同じファイルの再選択に対応
        });

        // ドラッグ＆ドロップ対応 (チャット入力枠エリア)
        const chatInputBox = document.querySelector('.input-box-wrapper');
        chatInputBox.addEventListener('dragover', (e) => {
            e.preventDefault();
            chatInputBox.style.borderColor = 'var(--primary-color)';
        });

        chatInputBox.addEventListener('dragleave', () => {
            chatInputBox.style.borderColor = 'var(--panel-border)';
        });

        chatInputBox.addEventListener('drop', (e) => {
            e.preventDefault();
            chatInputBox.style.borderColor = 'var(--panel-border)';
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                handleSelectedFiles(e.dataTransfer.files);
            }
        });

        // 選択されたファイルの処理
        function handleSelectedFiles(files) {
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                // 重複チェック
                if (attachedFiles.some(f => f.name === file.name && f.size === file.size)) continue;
                attachedFiles.push(file);
            }
            updateFilePreviews();
        }

        // ファイルプレビューの描画
        function updateFilePreviews() {
            previewContainer.innerHTML = '';
            if (attachedFiles.length === 0) {
                previewContainer.style.display = 'none';
                return;
            }
            previewContainer.style.display = 'flex';

            attachedFiles.forEach((file, idx) => {
                const item = document.createElement('div');
                item.style.position = 'relative';
                item.style.display = 'flex';
                item.style.alignItems = 'center';
                item.style.background = 'rgba(255,255,255,0.08)';
                item.style.border = '1px solid rgba(255,255,255,0.1)';
                item.style.borderRadius = '8px';
                item.style.padding = '4px 28px 4px 8px';
                item.style.fontSize = '0.8rem';
                item.style.color = 'var(--text-main)';
                item.style.maxWidth = '180px';
                item.style.whiteSpace = 'nowrap';
                item.style.overflow = 'hidden';
                item.style.textOverflow = 'ellipsis';

                // 画像の場合はサムネイルを表示
                if (file.type.startsWith('image/')) {
                    const img = document.createElement('img');
                    img.style.width = '24px';
                    img.style.height = '24px';
                    img.style.objectFit = 'cover';
                    img.style.borderRadius = '4px';
                    img.style.marginRight = '6px';
                    item.appendChild(img);

                    const reader = new FileReader();
                    reader.onload = (e) => {
                        img.src = e.target.result;
                    };
                    reader.readAsDataURL(file);
                } else {
                    // ドキュメント用アイコン (SVG)
                    const icon = document.createElement('span');
                    icon.innerHTML = `
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:6px; color:#a5b4fc; display:inline-block; vertical-align:middle;">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                            <line x1="16" y1="13" x2="8" y2="13"></line>
                            <line x1="16" y1="17" x2="8" y2="17"></line>
                            <polyline points="10 9 9 9 8 9"></polyline>
                        </svg>
                    `;
                    item.appendChild(icon);
                }

                const nameLabel = document.createElement('span');
                nameLabel.textContent = file.name;
                nameLabel.style.overflow = 'hidden';
                nameLabel.style.textOverflow = 'ellipsis';
                item.appendChild(nameLabel);

                // 削除ボタン (×)
                const delBtn = document.createElement('span');
                delBtn.textContent = '×';
                delBtn.style.position = 'absolute';
                delBtn.style.right = '6px';
                delBtn.style.top = '50%';
                delBtn.style.transform = 'translateY(-50%)';
                delBtn.style.cursor = 'pointer';
                delBtn.style.color = 'var(--text-muted)';
                delBtn.style.fontWeight = 'bold';
                delBtn.style.fontSize = '1rem';
                delBtn.style.padding = '2px';
                delBtn.addEventListener('click', () => {
                    attachedFiles.splice(idx, 1);
                    updateFilePreviews();
                });
                item.appendChild(delBtn);

                previewContainer.appendChild(item);
            });
        }

        // URL入力時
        apiUrlInput.addEventListener('change', () => {
            let url = apiUrlInput.value.trim();
            if (url.endsWith('/')) url = url.slice(0, -1);
            if (url.endsWith('/v1')) url = url.slice(0, -3);
            apiUrlInput.value = url;
            localStorage.setItem('colab_chat_api_url', url);
            checkConnection(url);
        });

        // 接続テスト
        async function checkConnection(baseUrl) {
            if (!baseUrl) {
                updateStatus(false, 'URLが空です');
                return;
            }
            updateStatus(false, '接続中...');
            try {
                const response = await fetch(`${baseUrl}/v1/models`, {
                    method: 'GET',
                    headers: { 'Accept': 'application/json' }
                });
                if (response.ok) {
                    const data = await response.json();
                    updateStatus(true, '接続成功');
                    populateModels(data.data);
                } else {
                    updateStatus(false, `エラー: ${response.status}`);
                }
            } catch (err) {
                console.error(err);
                updateStatus(false, '接続失敗 (疎通できません)');
            }
        }

        function updateStatus(connected, text) {
            statusIndicator.className = connected ? 'status-connected' : '';
            statusText.textContent = text;
        }

        function populateModels(models) {
            modelSelect.innerHTML = '';
            if (!models || models.length === 0) {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = 'モデルが見つかりません';
                modelSelect.appendChild(opt);
                return;
            }
            models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.id;
                opt.textContent = m.id;
                modelSelect.appendChild(opt);
            });
            headerModelName.textContent = modelSelect.value;
        }

        modelSelect.addEventListener('change', () => {
            headerModelName.textContent = modelSelect.value;
        });

        // UI追加用
        function appendMessage(role, text) {
            const wrapper = document.createElement('div');
            wrapper.className = 'message-wrapper';
            
            const message = document.createElement('div');
            message.className = `message message-${role}`;
            
            if (role === 'assistant') {
                message.innerHTML = marked.parse(text);
                message.querySelectorAll('pre code').forEach((el) => {
                    Prism.highlightElement(el);
                });
                addSaveButtonsToCodeBlocks(message);
            } else {
                message.textContent = text;
            }
            
            wrapper.appendChild(message);
            messageList.appendChild(wrapper);
            messageList.scrollTop = messageList.scrollHeight;
            return message;
        }

        // Web検索ロジック (CORS制限を100%回避するため、ローカルのPythonサーバー経由でAPIリクエストを中継する設計)
        async function performWebSearch(query) {
            const statusDiv = document.createElement('div');
            statusDiv.className = 'search-status';
            statusDiv.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>
                <span>Webを検索中: "${query}"...</span>
            `;
            messageList.appendChild(statusDiv);
            messageList.scrollTop = messageList.scrollHeight;

            // ローカルサーバーの /search エンドポイントを叩く (CORSエラーは100%回避)
            const searchUrl = `/search?q=${encodeURIComponent(query)}`;

            try {
                const response = await fetch(searchUrl);
                if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
                
                const results = await response.json();

                statusDiv.remove(); // 検索ステータスを消す

                if (results && results.length > 0) {
                    appendSearchResultsPanel(results);
                } else {
                    const failDiv = document.createElement('div');
                    failDiv.className = 'search-status';
                    failDiv.style.borderColor = 'var(--panel-border)';
                    failDiv.style.color = 'var(--text-muted)';
                    failDiv.innerHTML = `<span>検索結果が見つかりませんでした。</span>`;
                    messageList.appendChild(failDiv);
                    setTimeout(() => failDiv.remove(), 3000);
                }

                return results;

            } catch (e) {
                console.error('Search failed:', e);
                statusDiv.remove();
                
                // 検索失敗通知を画面に表示
                const errDiv = document.createElement('div');
                errDiv.className = 'search-status';
                errDiv.style.borderColor = 'var(--danger-color)';
                errDiv.style.color = 'var(--danger-color)';
                errDiv.innerHTML = `<span>⚠️ 検索サーバー接続エラー (スキップして回答します)</span>`;
                messageList.appendChild(errDiv);
                setTimeout(() => errDiv.remove(), 5000);
                
                return [];
            }
        }

        // 検索結果パネルの描画
        function appendSearchResultsPanel(results) {
            const panel = document.createElement('div');
            panel.className = 'search-results-panel';
            
            const title = document.createElement('div');
            title.className = 'search-results-title';
            title.innerHTML = `
                <span>🔍 ${results.length} 件のWeb検索結果を参照しました</span>
                <span class="arrow" style="transition: transform 0.2s">▼</span>
            `;
            
            const content = document.createElement('div');
            content.className = 'search-results-content';
            
            results.forEach(r => {
                const item = document.createElement('div');
                item.className = 'search-item';
                
                let cleanUrl = r.url;
                try {
                    if (cleanUrl.includes('uddg=')) {
                        const parts = cleanUrl.split('uddg=');
                        if (parts.length > 1) {
                            cleanUrl = decodeURIComponent(parts[1].split('&')[0]);
                        }
                    } else if (cleanUrl.startsWith('//')) {
                        cleanUrl = 'https:' + cleanUrl;
                    }
                } catch (urlErr) {
                    console.error('URL parse error:', urlErr);
                }

                item.innerHTML = `
                    <a href="${cleanUrl}" target="_blank" class="search-item-title">${r.title}</a>
                    <span class="search-item-snippet">${r.snippet}</span>
                `;
                content.appendChild(item);
            });

            panel.appendChild(title);
            panel.appendChild(content);
            messageList.appendChild(panel);
            messageList.scrollTop = messageList.scrollHeight;

            // 折りたたみロジック
            title.addEventListener('click', () => {
                const isHidden = content.style.display === 'none';
                content.style.display = isHidden ? 'flex' : 'none';
                title.querySelector('.arrow').style.transform = isHidden ? 'rotate(0deg)' : 'rotate(-90deg)';
            });
        }

        clearBtn.addEventListener('click', () => {
            conversationHistory = [];
            messageList.innerHTML = '';
            currentThreadId = 'thread-' + Date.now() + '-' + Math.random().toString(36).substring(2, 9);
            appendMessage('assistant', '会話履歴をクリアしました。新しいメッセージを入力してください。');
        });

        // 過去ログ検索機能 (過去ログRAG用)
        async function performHistorySearch(query) {
            const statusDiv = document.createElement('div');
            statusDiv.className = 'search-status';
            statusDiv.style.borderColor = '#10b981';
            statusDiv.style.color = '#10b981';
            statusDiv.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px; height:16px; margin-right:8px;"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                <span>過去ログを検索中: "${query}"...</span>
            `;
            messageList.appendChild(statusDiv);
            messageList.scrollTop = messageList.scrollHeight;

            const searchUrl = `/search-history?q=${encodeURIComponent(query)}`;

            try {
                const response = await fetch(searchUrl);
                if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
                
                const results = await response.json();
                statusDiv.remove();

                if (results && results.length > 0) {
                    const panel = document.createElement('div');
                    panel.className = 'search-results-panel';
                    panel.style.borderColor = 'rgba(16, 185, 129, 0.3)';
                    
                    const title = document.createElement('div');
                    title.className = 'search-results-title';
                    title.style.color = '#34d399';
                    title.innerHTML = `
                        <span>📜 過去の会話を ${results.length} 件参照しました</span>
                        <span class="arrow" style="transition: transform 0.2s">▼</span>
                    `;
                    
                    const content = document.createElement('div');
                    content.className = 'search-results-content';
                    
                    results.forEach((r, idx) => {
                        const item = document.createElement('div');
                        item.className = 'search-item';
                        
                        const summaryText = r.messages.map(m => `${m.role === 'user' ? '質問' : '回答'}: ${m.content}`).join('\n');
                        
                        item.innerHTML = `
                            <div class="search-item-title" style="color:var(--text-main); font-weight:600;">過去スレッド ${idx+1} (${new Date(r.timestamp).toLocaleString('ja-JP')})</div>
                            <pre style="background:rgba(0,0,0,0.2); padding:8px; border-radius:6px; font-size:0.8rem; white-space:pre-wrap; margin-top:4px; color:var(--text-muted);">${summaryText}</pre>
                        `;
                        content.appendChild(item);
                    });

                    panel.appendChild(title);
                    panel.appendChild(content);
                    messageList.appendChild(panel);
                    messageList.scrollTop = messageList.scrollHeight;

                    // 折りたたみロジック
                    title.addEventListener('click', () => {
                        const isHidden = content.style.display === 'none';
                        content.style.display = isHidden ? 'flex' : 'none';
                        title.querySelector('.arrow').style.transform = isHidden ? 'rotate(0deg)' : 'rotate(-90deg)';
                    });
                }

                return results;
            } catch (e) {
                console.error('History search failed:', e);
                statusDiv.remove();
                return [];
            }
        }

        // 会話履歴保存機能
        async function saveHistoryToServer() {
            if (conversationHistory.length === 0) return;
            try {
                await fetch('/save-history', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        id: currentThreadId,
                        messages: conversationHistory
                    })
                });
            } catch (e) {
                console.error('Failed to save history:', e);
            }
        }

        // PDFテキスト抽出ヘルパー
        async function extractTextFromPDF(file) {
            try {
                const arrayBuffer = await file.arrayBuffer();
                const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
                let extractedText = "";
                for (let i = 1; i <= pdf.numPages; i++) {
                    const page = await pdf.getPage(i);
                    const content = await page.getTextContent();
                    extractedText += content.items.map(item => item.str).join(" ") + "\n";
                }
                return extractedText;
            } catch (err) {
                console.error("PDF text extraction failed:", err);
                return `[PDF抽出エラー: ${file.name}]`;
            }
        }

        // メッセージ送信 (ReActループ対応)
        async function sendMessage() {
            const text = chatInput.value.trim();
            const provider = apiProviderSelect.value;
            const baseUrl = apiUrlInput.value.trim();
            const apiKey = apiKeyInput.value.trim();
            const model = modelSelect.value === 'custom' ? modelCustomInput.value.trim() : modelSelect.value;

            // テキストも添付ファイルも無ければ送信しない
            if (!text && attachedFiles.length === 0) return;
            if (!baseUrl || !model) {
                alert('先にAPI接続設定とモデル選択を完了させてください。');
                return;
            }
            const preset = PROVIDER_PRESETS[provider];
            if (preset && preset.requiresKey && !apiKey) {
                alert('このプロバイダにはAPIキーの入力が必要です。');
                return;
            }

            // AbortControllerおよびキャンセルフラグの初期化
            isCancelled = false;
            currentAbortController = new AbortController();
            
            // キャンセルボタンを表示し、送信ボタンを非活性化
            const cancelBtn = document.getElementById('cancel-btn');
            if (cancelBtn) cancelBtn.style.display = 'flex';
            if (sendBtn) sendBtn.disabled = true;

            try {
                chatInput.value = '';
                chatInput.style.height = '60px';

            const currentFiles = [...attachedFiles];
            attachedFiles = [];
            updateFilePreviews();

            const userMsgDiv = appendMessage('user', text || "(添付メディアのみ)");
            
            // 非同期で画像（Base64）およびドキュメント（テキスト）の抽出
            const imagesData = [];
            const docTexts = [];

            for (const file of currentFiles) {
                if (file.type.startsWith('image/')) {
                    const base64 = await new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onload = (e) => resolve(e.target.result);
                        reader.readAsDataURL(file);
                    });
                    imagesData.push(base64);

                    // チャット画面上に画像をインライン描画
                    const imgElement = document.createElement('img');
                    imgElement.src = base64;
                    imgElement.style.maxWidth = '280px';
                    imgElement.style.maxHeight = '280px';
                    imgElement.style.borderRadius = '12px';
                    imgElement.style.marginTop = '8px';
                    imgElement.style.display = 'block';
                    imgElement.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
                    userMsgDiv.appendChild(imgElement);
                } else if (file.name.endsWith('.pdf')) {
                    const pdfText = await extractTextFromPDF(file);
                    docTexts.push(`--- PDFファイル: ${file.name} ---\n${pdfText}`);
                } else {
                    // テキスト / CSV
                    const txt = await new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onload = (e) => resolve(e.target.result);
                        reader.readAsText(file);
                    });
                    docTexts.push(`--- ファイル: ${file.name} ---\n${txt}`);
                }
            }

            // 有効化されたスキルの内容を非同期でロード
            let skillInstructions = "";
            const enabledSkills = JSON.parse(localStorage.getItem('colab_chat_enabled_skills') || '[]');
            if (enabledSkills.length > 0) {
                try {
                    const skillPromises = enabledSkills.map(async (skillId) => {
                        const res = await fetch(`/get-skill?name=${encodeURIComponent(skillId)}`);
                        if (res.ok) {
                            const text = await res.text();
                            return `\n【スキル: ${skillId}】\n${text}\n`;
                        }
                        return "";
                    });
                    const results = await Promise.all(skillPromises);
                    skillInstructions = results.filter(t => t).join("\n");
                } catch (e) {
                    console.error("Skills loading failed:", e);
                }
            }

            let finalPromptText = text;

            // RAG: Web検索がONの場合
            if (searchToggle.checked) {
                const searchResults = await performWebSearch(text);
                if (searchResults && searchResults.length > 0) {
                    const contextString = searchResults.map((r, i) => {
                        let cleanUrl = r.url;
                        try {
                            if (cleanUrl.includes('uddg=')) {
                                const parts = cleanUrl.split('uddg=');
                                if (parts.length > 1) {
                                    cleanUrl = decodeURIComponent(parts[1].split('&')[0]);
                                }
                            } else if (cleanUrl.startsWith('//')) {
                                cleanUrl = 'https:' + cleanUrl;
                            }
                        } catch(e) {}
                        return `[検索結果 ${i+1}]\nタイトル: ${r.title}\nURL: ${cleanUrl}\n内容: ${r.snippet}`;
                    }).join('\n\n');
                    
                    finalPromptText = `ユーザーの質問に対して、以下のWeb検索結果を参照して回答してください。\n現在の年は2026年です。検索結果の記述が最新の情報になります。回答時には、適宜参照元のURLを提示してください。\n\n【Web検索結果】\n${contextString}\n\n【ユーザーの質問】\n${text}`;
                }
            }

            // 過去ログRAG: トグルがONの場合
            if (historyRagToggle.checked) {
                const historyResults = await performHistorySearch(text);
                if (historyResults && historyResults.length > 0) {
                    const contextString = historyResults.map((r, i) => {
                        // 過去の会話履歴内に画像等（配列オブジェクト）がある場合を考慮して正規化
                        const threadMsgs = r.messages.map(m => {
                            let contentStr = "";
                            if (Array.isArray(m.content)) {
                                contentStr = m.content.map(c => c.type === 'text' ? c.text : "[画像データ]").join(" ");
                            } else {
                                contentStr = m.content;
                            }
                            return `  ${m.role === 'user' ? 'ユーザー' : 'AI'}: ${contentStr}`;
                        }).join('\n');
                        return `[過去の会話スレッド ${i+1} (日時: ${new Date(r.timestamp).toLocaleString('ja-JP')})]\n${threadMsgs}`;
                    }).join('\n\n');
                    
                    finalPromptText = `ユーザーの質問に対して、過去のやり取りも参照して回答してください。\n\n【関連する過去の会話履歴】\n${contextString}\n\n【ユーザーの現在の質問】\n${finalPromptText}`;
                }
            }

            // 添付ドキュメントのテキスト内容をプロンプトに結合
            if (docTexts.length > 0) {
                finalPromptText = `${finalPromptText}\n\n【添付されたドキュメント・ファイルの内容】\n${docTexts.join('\n\n')}`;
            }

            // OpenAI Vision API形式のcontentオブジェクト構築
            let historyContent = finalPromptText;
            if (imagesData.length > 0) {
                historyContent = [{ type: 'text', text: finalPromptText }];
                imagesData.forEach(img => {
                    historyContent.push({
                        type: 'image_url',
                        image_url: { url: img }
                    });
                });
            }

            conversationHistory.push({ role: 'user', content: historyContent });

            const tempHistory = [...conversationHistory];
            tempHistory[tempHistory.length - 1] = { role: 'user', content: historyContent };

            let loopCount = 0;
            const isAgent = agentModeToggle && agentModeToggle.checked;
            const maxLoops = isAgent ? 10 : 3; // エージェントモード時は最大10ループ
            let isFirstTurn = true;

            while (loopCount < maxLoops) {
                if (isCancelled) {
                    appendMessage('assistant', '🛑 処理がユーザーによって中断されました。');
                    break;
                }
                const waitMsg = isAgent ? `🤖 エージェント自律実行中... (ステップ ${loopCount + 1}/${maxLoops})` : '⏳ 応答待ち...';
                const assistantMsgDiv = appendMessage('assistant', waitMsg);
                let systemPrompt = systemPromptInput.value.trim();
                
                if (isAgent) {
                    systemPrompt += `\n\n【動作モード: エージェントモード (Google Antigravity 互換)】
あなたは「Google Antigravity」エージェントとして動作します。
ユーザーから開発・修正などの大きなタスク（Goal）を指示された場合、以下の「計画・実行・検証ワークフロー」を厳格に実行してください：

1. [計画段階]: 最初のリターンで、作業フォルダの root に 'implementation_plan.md' ファイルを作成（または更新）し、そこに詳細な実装計画を記述してください。この時、実際のコード変更は行わず、まず計画を提示してユーザーの指示を仰ぎます。
2. [タスク整理]: 計画が提示できたら、次に 'task.md' を作成して TODO リストを記述します。
3. [自律実行]: 作成した TODO リストに従って、<write_file> タグを用いてファイルを直接作成・修正し、<run_command> を使ってビルドやテストを行いながら、自律的にタスクを完了させてください。進捗に応じて 'task.md' のチェックマークを更新します。
4. [検証と報告]: 最後にテストを実行して動作を検証し、変更内容の要約を 'walkthrough.md' にまとめて完了を報告してください。`;
                }

                if (skillInstructions) {
                    systemPrompt += "\n\n=== 有効化されたAIスキル指示 ===\n" + skillInstructions + "\n================================\n";
                }

                // o1/o3シリーズなどの推論モデルの判定
                const isO1orO3 = model && (model.startsWith('o1-') || model.startsWith('o3-') || model === 'o1');

                const messages = [];
                if (systemPrompt) {
                    messages.push({ role: isO1orO3 ? 'developer' : 'system', content: systemPrompt });
                }

                // エージェントモード時に、モデルに対する自律ツールのFew-shot（模範例）をインジェクション
                if (isAgent) {
                    messages.push(
                        { role: 'user', content: "作業フォルダに hello.py を作成して実行してください。" },
                        { role: 'assistant', content: `<write_file path="hello.py">\nprint("Hello World")\n</write_file>` },
                        { role: 'user', content: "[システム] ファイル hello.py の書き込みが完了しました。" },
                        { role: 'assistant', content: `<run_command>\npython hello.py\n</run_command>` },
                        { role: 'user', content: "[システム] コマンド実行結果: 終了コード: 0\n[STDOUT]\nHello World\n" },
                        { role: 'assistant', content: "hello.py ファイルの作成と実行が完了しました。出力結果は 'Hello World' です。" }
                    );
                }

                messages.push(...tempHistory);

                // APIリクエストのURL・ヘッダー・ペイロードの動的構築
                let requestUrl = "";
                const headers = { 'Content-Type': 'application/json' };
                let requestBody = {};
                let baseCleanUrl = baseUrl.replace(/\/$/, "");

                if (provider === 'colab') {
                    if (!baseCleanUrl.endsWith('/v1')) {
                        requestUrl = `${baseCleanUrl}/v1/chat/completions`;
                    } else {
                        requestUrl = `${baseCleanUrl}/chat/completions`;
                    }
                } else {
                    requestUrl = "/proxy/chat/completions";
                    headers['X-Provider'] = provider;
                    headers['X-Api-Key'] = apiKey;
                    headers['X-Base-Url'] = baseCleanUrl;
                }

                requestBody = {
                    model: model,
                    messages: messages,
                    stream: true
                };

                if (isO1orO3) {
                    // o1/o3モデルでは max_tokens がサポート外のため max_completion_tokens を使用
                    requestBody.max_completion_tokens = parseInt(maxTokensInput.value) || 2048;
                } else {
                    requestBody.temperature = parseFloat(tempInput.value) || 0.5;
                    requestBody.max_tokens = parseInt(maxTokensInput.value) || 2048;
                }

                // デバッグログ: 送信プロンプトと有効スキルをコンソールに出力
                console.log("[DEBUG] 送信されるシステムプロンプト全文:", systemPrompt);
                if (skillInstructions) {
                    console.log("[DEBUG] 注入されたAIスキル指示一覧:\n", skillInstructions);
                }

                let assistantResponseText = '';
                let assistantResponseReasoning = '';
                try {
                    const response = await fetch(requestUrl, {
                        method: 'POST',
                        headers: headers,
                        body: JSON.stringify(requestBody),
                        signal: currentAbortController ? currentAbortController.signal : undefined
                    });

                    if (!response.ok) {
                        let detailedError = `HTTP Error: ${response.status}`;
                        try {
                            const errJson = await response.json();
                            if (errJson && errJson.error) {
                                detailedError = errJson.error;
                            }
                        } catch (e) {
                            try {
                                const errText = await response.text();
                                if (errText) detailedError = `${detailedError} - ${errText}`;
                            } catch (e2) {}
                        }
                        throw new Error(detailedError);
                    }

                    const reader = response.body.getReader();
                    const decoder = new TextDecoder('utf-8');
                    assistantMsgDiv.textContent = ''; // 初期化

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        const chunk = decoder.decode(value, { stream: true });
                        const lines = chunk.split('\n');

                        for (const line of lines) {
                            const cleanedLine = line.trim();
                            if (!cleanedLine.startsWith('data:')) continue;
                            
                            const dataStr = cleanedLine.slice(5).trim();
                            if (dataStr === '[DONE]') continue;

                            try {
                                const parsed = JSON.parse(dataStr);
                                let deltaContent = "";
                                let deltaReasoning = "";

                                if (provider === 'claude') {
                                    if (parsed.type === 'content_block_delta' && parsed.delta && parsed.delta.text) {
                                        deltaContent = parsed.delta.text;
                                    }
                                } else {
                                    if (parsed.choices && parsed.choices[0] && parsed.choices[0].delta) {
                                        deltaContent = parsed.choices[0].delta.content || "";
                                        deltaReasoning = parsed.choices[0].delta.reasoning_content || "";
                                    }
                                }

                                if (deltaReasoning) {
                                    assistantResponseReasoning += deltaReasoning;
                                }
                                if (deltaContent) {
                                    assistantResponseText += deltaContent;
                                }

                                if (deltaReasoning || deltaContent) {
                                    let html = "";
                                    if (assistantResponseReasoning) {
                                        html += `<details open style="margin-bottom: 12px; background: rgba(255,255,255,0.02); border: 1px solid var(--panel-border); border-radius: 8px; padding: 10px;"><summary style="font-size:0.8rem; font-weight:600; color:var(--text-muted); cursor:pointer; outline:none; list-style:none; display:flex; align-items:center; gap:6px;">🧠 思考プロセス</summary><div style="font-size:0.85rem; color:var(--text-muted); font-style:italic; white-space:pre-wrap; margin-top:8px; line-height:1.5;">${assistantResponseReasoning}</div></details>`;
                                    }
                                    if (assistantResponseText) {
                                        html += marked.parse(assistantResponseText);
                                    } else if (assistantResponseReasoning) {
                                        html += `<span style="color:var(--text-muted); font-size:0.85rem; display:inline-block; margin-top:4px;">⏳ 思考中...</span>`;
                                    }

                                    assistantMsgDiv.innerHTML = html;
                                    assistantMsgDiv.querySelectorAll('pre code').forEach((el) => {
                                        Prism.highlightElement(el);
                                    });
                                    messageList.scrollTop = messageList.scrollHeight;
                                }
                            } catch (e) {}
                        }
                    }

                    // ストリーミング完了後にコードブロックに保存ボタンを付与
                    addSaveButtonsToCodeBlocks(assistantMsgDiv);

                    // 履歴に追加
                    tempHistory.push({ role: 'assistant', content: assistantResponseText });
                    if (isFirstTurn) {
                        conversationHistory.push({ role: 'assistant', content: assistantResponseText });
                        isFirstTurn = false;
                    } else {
                        conversationHistory.push({ role: 'assistant', content: assistantResponseText });
                    }

                } catch (err) {
                    console.error(err);
                    assistantMsgDiv.innerHTML = `<span style="color:var(--danger-color)">❌ エラーが発生しました: ${err.message}</span>`;
                    break;
                }

                if (isCancelled) {
                    appendMessage('assistant', '🛑 処理がユーザーによって中断されました。');
                    break;
                }

                // AIによるツール呼び出しタグが含まれているかチェック (思考プロセス内も含めて検索)
                const fullTextToSearch = (assistantResponseText || "") + "\n" + (assistantResponseReasoning || "");
                const writeMatch = fullTextToSearch.match(/<write_file\s+path="([^"]+)">([\s\S]*?)<\/write_file>/);
                const readMatch = fullTextToSearch.match(/<read_file\s+path="([^"]+)"\s*\/?>/);
                const cmdMatch = fullTextToSearch.match(/<run_command>([\s\S]*?)<\/run_command>/) || fullTextToSearch.match(/<execute_command>(.*?)<\/execute_command>/s);

                if (writeMatch || readMatch || cmdMatch) {
                    loopCount++;
                    let toolName = "";
                    let toolArg = "";
                    let fetchUrl = "";
                    let payload = {};
                    let statusText = "";
                    let iconSvg = "";
                    let color = "#a5b4fc";

                    if (writeMatch) {
                        toolName = "write_file";
                        const path = writeMatch[1].trim();
                        const content = writeMatch[2];
                        toolArg = path;
                        fetchUrl = "/write-file";
                        payload = { path, content };
                        statusText = `🤖 AIがファイルを書き込み中: "${path}"...`;
                        iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="animation: spin 2s linear infinite; width:16px; height:16px; margin-right:8px;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="12" y1="18" x2="12" y2="12"></line><line x1="9" y1="15" x2="15" y2="15"></line></svg>`;
                    } else if (readMatch) {
                        toolName = "read_file";
                        const path = readMatch[1].trim();
                        toolArg = path;
                        fetchUrl = "/read-file";
                        payload = { path };
                        statusText = `🤖 AIがファイルを読み取り中: "${path}"...`;
                        iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="animation: spin 2s linear infinite; width:16px; height:16px; margin-right:8px;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>`;
                    } else if (cmdMatch) {
                        toolName = "run_command";
                        const cmd = cmdMatch[1].trim();
                        toolArg = cmd;
                        fetchUrl = "/run-command";
                        payload = { command: cmd };
                        statusText = `🤖 AIがコマンドを実行中: "${cmd}"...`;
                        iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="animation: spin 2s linear infinite; width:16px; height:16px; margin-right:8px;"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>`;
                    }

                    // ステータス表示の追加
                    const statusDiv = document.createElement('div');
                    statusDiv.className = 'search-status';
                    statusDiv.style.borderColor = color;
                    statusDiv.style.color = color;
                    statusDiv.innerHTML = `${iconSvg}<span>${statusText}</span>`;
                    messageList.appendChild(statusDiv);
                    messageList.scrollTop = messageList.scrollHeight;

                    try {
                        const toolResponse = await fetch(fetchUrl, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(payload)
                        });

                        statusDiv.remove();

                        let resultText = '';
                        if (!toolResponse.ok) {
                            let errReason = '不明なエラー';
                            try {
                                const errJson = await toolResponse.json();
                                errReason = errJson.error || errReason;
                            } catch (e) {
                                errReason = await toolResponse.text().catch(() => errReason);
                            }
                            resultText = `エラー (${toolResponse.status}): ${errReason}`;
                        } else {
                            if (toolName === 'write_file') {
                                resultText = `[成功] ファイルの書き込みが正常に完了しました。`;
                            } else if (toolName === 'read_file') {
                                const data = await toolResponse.json();
                                resultText = data.content;
                            } else if (toolName === 'run_command') {
                                const data = await toolResponse.json();
                                resultText = `終了コード: ${data.returncode}\n`;
                                if (data.stdout) resultText += `[STDOUT]\n${data.stdout}\n`;
                                if (data.stderr) resultText += `[STDERR]\n${data.stderr}\n`;
                                if (!data.stdout && !data.stderr) resultText += `(出力なし)`;
                            }
                        }

                        // 画面上に実行結果パネルを描画
                        const resultPanel = document.createElement('div');
                        resultPanel.className = 'search-results-panel';
                        let displayTitle = "";
                        if (toolName === 'write_file') displayTitle = `💾 ファイル書き込み完了: "${toolArg}"`;
                        else if (toolName === 'read_file') displayTitle = `📖 ファイル読み込み完了: "${toolArg}"`;
                        else displayTitle = `🐚 コマンド実行結果: "${toolArg}"`;

                        resultPanel.innerHTML = `
                            <div class="search-results-title">
                                <span>${displayTitle}</span>
                                <span class="arrow" style="transition: transform 0.2s">▼</span>
                            </div>
                            <pre class="search-results-content" style="background:#07080d; color:#a3e635; padding:12px; border-radius:8px; font-family:'Fira Code',monospace; font-size:0.8rem; overflow-x:auto; white-space:pre-wrap; margin-top:8px;">${resultText}</pre>
                        `;
                        messageList.appendChild(resultPanel);
                        messageList.scrollTop = messageList.scrollHeight;

                        // 折りたたみロジック
                        const title = resultPanel.querySelector('.search-results-title');
                        const content = resultPanel.querySelector('.search-results-content');
                        title.addEventListener('click', () => {
                            const isHidden = content.style.display === 'none';
                            content.style.display = isHidden ? 'block' : 'none';
                            title.querySelector('.arrow').style.transform = isHidden ? 'rotate(0deg)' : 'rotate(-90deg)';
                        });

                        // ReActの入力として結果をインジェクション
                        const resultFeedback = `[ツール実行結果 - ${toolName}]\n${resultText}`;
                        tempHistory.push({ role: 'user', content: resultFeedback });
                        conversationHistory.push({ role: 'user', content: `[AIによるツール実行: ${toolName}] ${toolArg}` });

                    } catch (err) {
                        console.error(err);
                        statusDiv.remove();
                        const errFeedback = `[ツール実行エラー - ${toolName}] ${err.message}`;
                        tempHistory.push({ role: 'user', content: errFeedback });
                    }
                } else {
                    // ツールが呼び出されなかった場合はReActループを終了
                    break;
                }
            }
            
            // 会話履歴をサーバーに自動保存
            await saveHistoryToServer();
            } finally {
                resetGeneratingUI();
            }
        }

        // イベントリスナー
        sendBtn.addEventListener('click', sendMessage);

        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = `${chatInput.scrollHeight}px`;
        });

        // タブ切り替えロジック
        const tabChatBtn = document.getElementById('tab-chat-btn');
        const tabTermBtn = document.getElementById('tab-term-btn');
        const chatPanel = document.getElementById('chat-panel');
        const terminalPanel = document.getElementById('terminal-panel');

        tabChatBtn.addEventListener('click', () => {
            tabChatBtn.classList.add('active');
            tabChatBtn.style.color = 'var(--text-main)';
            tabChatBtn.style.borderBottomColor = 'var(--accent-color)';
            
            tabTermBtn.classList.remove('active');
            tabTermBtn.style.color = 'var(--text-muted)';
            tabTermBtn.style.borderBottomColor = 'transparent';

            chatPanel.style.display = 'flex';
            terminalPanel.style.display = 'none';
        });

        tabTermBtn.addEventListener('click', () => {
            tabTermBtn.classList.add('active');
            tabTermBtn.style.color = 'var(--text-main)';
            tabTermBtn.style.borderBottomColor = 'var(--accent-color)';
            
            tabChatBtn.classList.remove('active');
            tabChatBtn.style.color = 'var(--text-muted)';
            tabChatBtn.style.borderBottomColor = 'transparent';

            chatPanel.style.display = 'none';
            terminalPanel.style.display = 'flex';
        });

        // ターミナル実行ロジック
        const terminalInput = document.getElementById('terminal-input');
        const terminalRunBtn = document.getElementById('terminal-run-btn');
        const terminalOutput = document.getElementById('terminal-output');

        async function executeCommand(cmd) {
            if (!cmd) return;
            terminalOutput.textContent = `⏳ コマンドを実行中: ${cmd}\n`;
            terminalRunBtn.disabled = true;

            try {
                const response = await fetch('/run-command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: cmd })
                });

                if (!response.ok) {
                    const errText = await response.text();
                    terminalOutput.textContent = `❌ エラー (${response.status}): ${errText}`;
                    return;
                }

                const data = await response.json();
                
                let output = '';
                if (data.stdout) {
                    output += data.stdout;
                }
                if (data.stderr) {
                    output += `\n[STDERR]\n${data.stderr}`;
                }
                if (output === '') {
                    output = `(出力なし、終了コード: ${data.returncode})`;
                } else {
                    output += `\n\n(終了コード: ${data.returncode})`;
                }
                
                terminalOutput.textContent = output;

            } catch (err) {
                console.error(err);
                terminalOutput.textContent = `❌ 実行エラー: ${err.message}`;
            } finally {
                terminalRunBtn.disabled = false;
                terminalOutput.scrollTop = terminalOutput.scrollHeight;
            }
        }

        terminalRunBtn.addEventListener('click', () => {
            executeCommand(terminalInput.value.trim());
        });

        terminalInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                executeCommand(terminalInput.value.trim());
            }
        });

        // クイックコマンド実行
        window.runQuickCommand = function(cmd) {
            terminalInput.value = cmd;
            executeCommand(cmd);
        };

        // 続行 (Proceed) ボタンのイベントリスナー
        const proceedBtn = document.getElementById('proceed-btn');
        if (proceedBtn) {
            proceedBtn.addEventListener('click', () => {
                chatInput.value = "次のステップを実行してください。";
                sendMessage();
            });
        }

        // 中断 (Cancel) ボタンのイベントリスナー
        const cancelBtn = document.getElementById('cancel-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                isCancelled = true;
                if (currentAbortController) {
                    currentAbortController.abort();
                }
                resetGeneratingUI();
            });
        }