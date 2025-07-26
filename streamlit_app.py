
import streamlit as st
import pandas as pd
import easyocr
from PIL import Image
import numpy as np
import re
import fitz  # PyMuPDF
from io import BytesIO

st.set_page_config(page_title="📄 Facture phyto → Registre SMAG", layout="wide")
st.title("🔧 Analyse automatique de facture Terrena / CAPL (PDF ou image)")

uploaded = st.file_uploader("Téléverse une facture (PDF ou image)", type=["png", "jpg", "jpeg", "pdf"])
if uploaded:
    # Traitement PDF via PyMuPDF
    if uploaded.type == "application/pdf":
        doc = fitz.open(stream=uploaded.read(), filetype="pdf")
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=300)
        img = Image.open(BytesIO(pix.tobytes("png")))
    else:
        img = Image.open(uploaded)

    st.image(img, caption="Facture chargée", use_column_width=True)

    reader = easyocr.Reader(['fr'], gpu=False)
    result = reader.readtext(np.array(img), detail=0, paragraph=True)
    lignes = [line.strip() for line in result if line.strip()]
    texte = "\n".join(lignes)

    st.subheader("🧾 Texte extrait")
    st.text_area("", texte, height=200)

    produits = []
    date = ""
    fournisseur = ""
    known_keywords = ["DECIS", "TRICHO", "PROTECH", "SAC", "PHYTO"]

    for i, ligne in enumerate(lignes):
        if not date:
            d = re.search(r"(\d{2}/\d{2}/\d{4})", ligne)
            if d:
                date = d.group(1)
        if not fournisseur and ("Terrena" in ligne or "CAPL" in ligne):
            fournisseur = "Terrena" if "Terrena" in ligne else "CAPL"

        if any(keyword in ligne.upper() for keyword in known_keywords):
            bloc = " ".join(lignes[i:i+2])
            m = re.search(r"(DECIS.*?|TRICHO.*?)\s(\d{1,3}[,.]\d{2})", bloc)
            q = re.search(r"(\d{1,2}[,.]\d{1,2}|\d{1,3})\s?([LPCE]{1,3})", bloc)
            if m and q:
                produit = m.group(1).strip()
                prix = float(m.group(2).replace(",", "."))
                quantite = float(q.group(1).replace(",", "."))
                unite = q.group(2)
                produits.append({
                    "Date": date,
                    "Fournisseur": fournisseur,
                    "Produit": produit,
                    "Quantité": quantite,
                    "Unité": unite,
                    "Prix unitaire HT (€)": prix,
                    "Volume total": f"{quantite} {unite}"
                })

    if produits:
        df = pd.DataFrame(produits)
        st.success("✅ Produits détectés automatiquement :")
        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Télécharger le registre CSV", data=csv, file_name="registre_phyto.csv", mime="text/csv")
    else:
        st.warning("❌ Aucun produit détecté – essaie avec une facture plus lisible ou un PDF original.")
