.PHONY: install check coleta rebuild daily test dash
install: ; pip install -r requirements.txt
check:   ; python -m tcg check-colecao
coleta:  ; python -m tcg collect
rebuild: ; python -m tcg rebuild      # silver + gold + carteira, a partir do bruto
daily:   ; python -m tcg daily        # coleta + rebuild
test:    ; PYTHONPATH=src pytest -q
dash:    ; PYTHONPATH=src streamlit run dashboard/app.py
