# -*- coding: utf-8 -*-
"""
Generateur de Personas Marketing
Societe Generale Cote d'Ivoire
"""

import streamlit as st
import pandas as pd
import json
from openai import OpenAI
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

# Configuration Streamlit
st.set_page_config(
    page_title="Generateur de Personas Marketing",
    page_icon="🎯",
    layout="wide"
)

# CSS personnalise
st.markdown("""
    <style>
    .header {
        background: linear-gradient(135deg, #d32f2f 0%, #b71c1c 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .cluster-box {
        border-left: 5px solid #d32f2f;
        padding: 15px;
        background-color: #f5f5f5;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .persona-output {
        background-color: #fafafa;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="header">
        <h1>🎯 Generateur de Personas Marketing</h1>
        <p>Generez automatiquement des descriptions de personas pour chaque segment client</p>
    </div>
""", unsafe_allow_html=True)

# Initialiser la session
if "client" not in st.session_state:
    st.session_state.client = None
if "personas" not in st.session_state:
    st.session_state.personas = {}
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "produits_bancaires_text" not in st.session_state:
    st.session_state.produits_bancaires_text = None
if "loaded_segments" not in st.session_state:
    st.session_state.loaded_segments = None

# Sidebar - Configuration
with st.sidebar:
    st.header("Configuration")
    
    api_key = st.text_input("Cle API OpenAI", type="password", key="api_key")
    
    if api_key and st.session_state.client is None:
        try:
            st.session_state.client = OpenAI(api_key=api_key)
            st.success("Connecte a OpenAI !")
        except Exception as e:
            st.error(f"Erreur de connexion: {e}")
    
    st.divider()
    
    st.header("Catalogue Produits")
    
    uploaded_excel = st.file_uploader(
        "Charger le fichier Excel du catalogue produits",
        type=["xlsx", "xls"],
        help="Fichier Excel avec colonnes detaillees sur les produits bancaires"
    )
    
    if uploaded_excel is not None:
        try:
            df_produits = pd.read_excel(uploaded_excel)
            
            st.success(f"Excel charge ! ({len(df_produits)} produits)")
            st.info(f"Colonnes detectees: {', '.join(df_produits.columns.tolist())}")
            
            with st.expander("Apercu des produits"):
                st.dataframe(df_produits.head(10), use_container_width=True)
            
            # Convertir en texte structure
            catalogue_text = "CATALOGUE PRODUITS BANCAIRES (DETAILLE):\n\n"
            
            for idx, row in df_produits.iterrows():
                catalogue_text += f"--- PRODUIT {idx + 1} ---\n"
                for col in df_produits.columns:
                    value = str(row[col])
                    # Nettoyer les caracteres problematiques
                    value_clean = value.encode('ascii', 'ignore').decode('ascii')
                    catalogue_text += f"{col}: {value_clean}\n"
                catalogue_text += "\n"
            
            st.session_state.produits_bancaires_text = catalogue_text
            
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier Excel: {e}")
            st.info("Verifiez que le fichier Excel est valide et contient des donnees")
    
    if st.session_state.produits_bancaires_text:
        st.info("Catalogue produits charge en memoire")
        if st.button("Supprimer le catalogue"):
            st.session_state.produits_bancaires_text = None
            st.rerun()
    else:
        st.warning("Aucun catalogue charge")
        st.caption("Uploadez un fichier Excel avec les informations detaillees sur les produits bancaires")
    
    st.divider()
    
    st.header("Options")
    
    model_choice = st.selectbox(
        "Modele OpenAI",
        ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        index=0
    )
    
    st.divider()
    st.info("Configurez votre cle API OpenAI et chargez le catalogue produits pour commencer")

# Donnees des segments par defaut
segments_data = [
    {
        "id": 0,
        "name": "Les clients fideles et hyper-connectes",
        "age": 40,
        "nbProducts": 8,
        "revenueHommes": "100 000 - 200 000 FCFA",
        "revenueFemmes": "100 000 - 200 000 FCFA",
        "mobileAccess": "99%",
        "emailAccess": "85%",
        "characteristics": "Maturite professionnelle, clients de base stable"
    },
    {
        "id": 1,
        "name": "Les racines de confiance",
        "age": 62,
        "nbProducts": 8,
        "revenueHommes": "200 000 - 300 000 FCFA",
        "revenueFemmes": "0 - 100 000 FCFA",
        "mobileAccess": "97%",
        "emailAccess": "57%",
        "characteristics": "Anciens fonctionnaires, revenus constants"
    },
    {
        "id": 2,
        "name": "Les ambassadeurs de demain",
        "age": 36,
        "nbProducts": 3,
        "revenueHommes": "0 - 100 000 FCFA",
        "revenueFemmes": "0 - 100 000 FCFA",
        "mobileAccess": "98%",
        "emailAccess": "60%",
        "characteristics": "En transition professionnelle, hyper-connectes"
    },
    {
        "id": 3,
        "name": "Les champions fonctionnaires",
        "age": 44,
        "nbProducts": 14,
        "revenueHommes": "300 000 - 400 000 FCFA",
        "revenueFemmes": "0 - 100 000 FCFA",
        "mobileAccess": "99%",
        "emailAccess": "88%",
        "characteristics": "Plus grands utilisateurs, hyper-consommateurs"
    },
    {
        "id": 4,
        "name": "Les fideles discrets",
        "age": 41,
        "nbProducts": 3,
        "revenueHommes": "0 - 100 000 FCFA",
        "revenueFemmes": "0 - 100 000 FCFA",
        "mobileAccess": "98%",
        "emailAccess": "N/A",
        "characteristics": "Employes stables, utilisation minimale"
    }
]

def clean_text(text):
    """Nettoie le texte des caracteres problematiques"""
    if text is None:
        return "N/A"
    try:
        return str(text).encode('ascii', 'ignore').decode('ascii')
    except:
        return str(text)

def create_prompt(segment):
    """Construit le prompt pour OpenAI avec gestion d'encodage"""
    
    # Nettoyer toutes les valeurs du segment
    clean_segment = {k: clean_text(v) for k, v in segment.items()}
    
    base_info = f"""Generate a complete and detailed description of a marketing persona for a banking segment with the following characteristics:

Segment name: {clean_segment.get('name', 'N/A')}
Average age: {clean_segment.get('age', 'N/A')} years
Number of products used: {clean_segment.get('nbProducts', 'N/A')}
Monthly income (Men): {clean_segment.get('revenueHommes', 'N/A')}
Monthly income (Women): {clean_segment.get('revenueFemmes', 'N/A')}
Mobile accessibility: {clean_segment.get('mobileAccess', 'N/A')}
Email accessibility: {clean_segment.get('emailAccess', 'N/A')}
Main characteristics: {clean_segment.get('characteristics', 'N/A')}"""

    if st.session_state.produits_bancaires_text:
        # Nettoyer le texte du catalogue
        clean_pdf = clean_text(st.session_state.produits_bancaires_text[:10000])
        
        produits_info = f"""

AVAILABLE BANKING PRODUCTS CATALOG:
{clean_pdf}

RECOMMENDATION METHODOLOGY:
To recommend the most suitable products for this segment, analyze ALL the following criteria:

1. DEMOGRAPHIC PROFILE:
   - Average age ({clean_segment.get('age', 'N/A')} years) -> Needs according to life stage
   - Men/women income -> Financial capacity AND gender disparities
   
2. BANKING BEHAVIOR:
   - Current number of products ({clean_segment.get('nbProducts', 'N/A')}) -> Banking sophistication
   - If low (< 5) -> Under-banked segment, needs simple products
   - If high (> 8) -> Mature segment, needs premium services
   
3. DIGITAL CONNECTIVITY:
   - Mobile accessibility ({clean_segment.get('mobileAccess', 'N/A')}) -> Digital appetite
   - Email accessibility ({clean_segment.get('emailAccess', 'N/A')}) -> Preferred communication channels
   - If > 95% mobile -> Favor digital services (Mobile app, online banking)
   - If < 80% mobile -> Favor traditional services (branch, phone)
   
4. SOCIO-PROFESSIONAL CHARACTERISTICS:
   - {clean_segment.get('characteristics', 'N/A')}
   - Identify: professional status, stability, specific needs

5. PRODUCT RECOMMENDATION LOGIC (DO NOT BASE ONLY ON PRICE):
   - Match products with ACTUAL NEEDS based on the detailed catalog
   - Consider target segments mentioned in the catalog
   - Analyze product characteristics vs segment profile
   - Justify recommendations with specific catalog details

IMPORTANT:
- NEVER recommend a product only because it is expensive or prestigious
- ALWAYS justify based on REAL NEEDS of the segment
- Consider QUALITY-PRICE RATIO and ADEQUACY to uses
- Identify GAPS (missing products despite the need)
- Reference specific product details from the catalog"""
    else:
        produits_info = "\n\nNote: No product catalog loaded. Make general recommendations based on segment characteristics."
    
    prompt = base_info + produits_info + """

Provide a professional description in FRENCH including:

1. DETAILED DEMOGRAPHIC PROFILE
2. BANKING BEHAVIORS AND PATTERNS
3. NEEDS AND PREFERENCES
4. MOTIVATIONS AND PAIN POINTS
5. RECOMMENDED MARKETING STRATEGY
6. ADAPTED BANKING PRODUCT RECOMMENDATIONS
   
   For EACH recommended product, justify by citing:
   - Segment characteristics that justify it
   - Specific need covered
   - Adequacy with profile (age, income, connectivity, etc.)
   - Exact price from catalog
   - Why this product matches vs alternatives
   
   Structure:
   A. Priority Products (High priority)
   B. Complementary Products (Medium priority)
   C. Development Products (Long term)

7. UNIQUE VALUE PROPOSITION

Format: Use clear sections with bold titles. Write everything in FRENCH."""
    
    return prompt

def generate_persona_pdf(persona_id, persona_content, segment_name):
    """Genere un PDF formate pour un persona"""
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#d32f2f',
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor='#b71c1c',
        spaceAfter=12,
        spaceBefore=12
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_JUSTIFY,
        spaceAfter=10
    )
    
    story = []
    
    # Nettoyer le contenu
    clean_content = clean_text(persona_content)
    clean_name = clean_text(segment_name)
    
    story.append(Paragraph("PERSONA MARKETING", title_style))
    story.append(Paragraph(f"Cluster {persona_id}: {clean_name}", heading_style))
    story.append(Spacer(1, 0.5*cm))
    
    lines = clean_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.3*cm))
            continue
        
        if line.startswith('**') and line.endswith('**'):
            title_text = line.replace('**', '')
            story.append(Paragraph(title_text, heading_style))
        elif line.startswith('###'):
            title_text = line.replace('###', '').strip()
            story.append(Paragraph(title_text, heading_style))
        elif line.startswith('##'):
            title_text = line.replace('##', '').strip()
            story.append(Paragraph(title_text, heading_style))
        elif line.startswith('#'):
            title_text = line.replace('#', '').strip()
            story.append(Paragraph(title_text, heading_style))
        elif line.startswith('- ') or line.startswith('* '):
            text = line[2:].strip()
            story.append(Paragraph(f"- {text}", normal_style))
        else:
            text = line.replace('**', '')
            if text:
                story.append(Paragraph(text, normal_style))
    
    story.append(Spacer(1, 1*cm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor='gray',
        alignment=TA_CENTER
    )
    story.append(Paragraph("Genere par le Generateur de Personas Marketing - Societe Generale Cote d'Ivoire", footer_style))
    
    doc.build(story)
    
    buffer.seek(0)
    return buffer

def generate_persona(segment, model):
    """Genere un persona avec OpenAI"""
    if st.session_state.client is None:
        st.error("Veuillez d'abord configurer votre cle API OpenAI dans la barre laterale.")
        return None
    
    try:
        prompt = create_prompt(segment)
        
        message = st.session_state.client.chat.completions.create(
            model=model,
            max_tokens=3000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        result = message.choices[0].message.content
        st.session_state.personas[segment.get("id", 0)] = result
        return result
    
    except Exception as e:
        st.error(f"Erreur lors de la generation: {str(e)}")
        return None

# Onglets principaux
tab1, tab2, tab3 = st.tabs(["Segments", "Generer Personas", "Chat Intelligent"])

# TAB 1 - SEGMENTS
with tab1:
    st.subheader("Segments Clients Disponibles")
    
    data_source = st.radio(
        "Source de donnees",
        ["Donnees par defaut", "Charger un CSV personnalise"],
        index=0
    )
    
    if data_source == "Charger un CSV personnalise":
        st.divider()
        st.subheader("Charger vos propres donnees")
        uploaded_file = st.file_uploader("Chargez un fichier CSV avec vos segments", type="csv", key="csv_uploader")
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
                
                # Convertir en liste de dictionnaires
                segments_from_csv = df.to_dict('records')
                
                # Normaliser les noms de colonnes
                normalized_segments = []
                for seg in segments_from_csv:
                    normalized_seg = {}
                    for key, value in seg.items():
                        clean_key = key.strip().lower()
                        if 'id' in clean_key:
                            normalized_seg['id'] = value
                        elif 'name' in clean_key or 'nom' in clean_key:
                            normalized_seg['name'] = value
                        elif 'age' in clean_key:
                            normalized_seg['age'] = value
                        elif 'product' in clean_key or 'produit' in clean_key:
                            normalized_seg['nbProducts'] = value
                        elif 'homme' in clean_key or 'male' in clean_key:
                            normalized_seg['revenueHommes'] = value
                        elif 'femme' in clean_key or 'female' in clean_key:
                            normalized_seg['revenueFemmes'] = value
                        elif 'mobile' in clean_key:
                            normalized_seg['mobileAccess'] = value
                        elif 'email' in clean_key or 'mail' in clean_key:
                            normalized_seg['emailAccess'] = value
                        elif 'caract' in clean_key or 'character' in clean_key:
                            normalized_seg['characteristics'] = value
                        else:
                            normalized_seg[clean_key] = value
                    
                    normalized_segments.append(normalized_seg)
                
                st.session_state.loaded_segments = normalized_segments
                
                st.success(f"Fichier charge avec succes! ({len(normalized_segments)} segments)")
                st.dataframe(df, use_container_width=True)
                
                with st.expander("Colonnes detectees"):
                    st.write("Colonnes du CSV:", df.columns.tolist())
                    if normalized_segments:
                        st.write("Cles normalisees:", list(normalized_segments[0].keys()))
                
                current_segments = normalized_segments
            except Exception as e:
                st.error(f"Erreur lors du chargement du CSV: {e}")
                current_segments = []
        else:
            if st.session_state.loaded_segments:
                current_segments = st.session_state.loaded_segments
                st.info(f"{len(current_segments)} segments charges en memoire")
            else:
                st.info("Veuillez charger un fichier CSV pour continuer")
                current_segments = []
    else:
        current_segments = segments_data
    
    if current_segments:
        st.divider()
        st.subheader("Segments a traiter")
        cols = st.columns(2)
        for idx, segment in enumerate(current_segments):
            with cols[idx % 2]:
                st.markdown(f"""
                <div class="cluster-box">
                    <h4>CLUSTER {segment.get('id', idx)}: {clean_text(segment.get('name', 'Sans nom'))}</h4>
                    <p><b>Age moyen:</b> {segment.get('age', 'N/A')} ans</p>
                    <p><b>Produits:</b> {segment.get('nbProducts', 'N/A')}</p>
                    <p><b>Revenu Hommes:</b> {clean_text(segment.get('revenueHommes', 'N/A'))}</p>
                    <p><b>Revenu Femmes:</b> {clean_text(segment.get('revenueFemmes', 'N/A'))}</p>
                    <p><b>Acces Mobile:</b> {segment.get('mobileAccess', 'N/A')}</p>
                    <p><b>Acces Email:</b> {segment.get('emailAccess', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)

# TAB 2 - GENERATION
with tab2:
    st.subheader("Generer des Personas")
    
    if "loaded_segments" in st.session_state and st.session_state.loaded_segments:
        segments_to_use = st.session_state.loaded_segments
    else:
        segments_to_use = segments_data
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.write("**Segments disponibles:**")
        selected_segments = st.multiselect(
            "Selectionnez les segments a traiter",
            options=[(s.get("id", idx), clean_text(s.get("name", f"Segment {idx}"))) for idx, s in enumerate(segments_to_use)],
            format_func=lambda x: f"Cluster {x[0]}: {x[1][:30]}...",
            default=[(segments_to_use[0].get("id", 0), clean_text(segments_to_use[0].get("name", "Segment 0")))]
        )
        
        if st.button("Generer les Personas", type="primary"):
            if not selected_segments:
                st.warning("Selectionnez au moins un segment")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, (seg_id, _) in enumerate(selected_segments):
                    segment = next((s for s in segments_to_use if s.get("id", -1) == seg_id), None)
                    if segment:
                        status_text.text(f"Generation du Cluster {seg_id}...")
                        
                        generate_persona(segment, model_choice)
                        
                        progress_bar.progress((idx + 1) / len(selected_segments))
                
                st.success("Tous les personas ont ete generes!")
    
    with col2:
        if st.session_state.personas:
            st.write("**Personas generes:**")
            
            persona_options = [
                f"Cluster {k}: {clean_text(next((s.get('name', 'Unknown') for s in segments_to_use if s.get('id', -1) == k), 'Unknown'))[:40]}..."
                for k in sorted(st.session_state.personas.keys())
            ]
            
            selected_persona = st.selectbox("Afficher le persona de:", persona_options)
            
            if selected_persona:
                persona_id = int(selected_persona.split(":")[0].replace("Cluster ", ""))
                
                st.markdown("---")
                st.markdown('<div class="persona-output">', unsafe_allow_html=True)
                st.markdown(st.session_state.personas[persona_id])
                st.markdown('</div>', unsafe_allow_html=True)
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.download_button(
                        label="Telecharger en TXT",
                        data=st.session_state.personas[persona_id],
                        file_name=f"persona_cluster_{persona_id}.txt",
                        mime="text/plain"
                    )
                
                with col_b:
                    segment_name = clean_text(next((s.get("name", "Unknown") for s in segments_to_use if s.get("id", -1) == persona_id), "Unknown"))
                    
                    pdf_buffer = generate_persona_pdf(persona_id, st.session_state.personas[persona_id], segment_name)
                    
                    st.download_button(
                        label="Telecharger en PDF",
                        data=pdf_buffer,
                        file_name=f"persona_cluster_{persona_id}.pdf",
                        mime="application/pdf"
                    )
        else:
            st.info("Generez des personas pour les voir ici")

# TAB 3 - CHAT
with tab3:
    st.subheader("Assistant Intelligent pour Personas")
    
    if st.session_state.client is None:
        st.warning("Veuillez configurer votre cle API OpenAI d'abord.")
    else:
        if "loaded_segments" in st.session_state and st.session_state.loaded_segments:
            segments_for_chat = st.session_state.loaded_segments
        else:
            segments_for_chat = segments_data
        
        st.write("**Personas generes disponibles:**")
        if st.session_state.personas:
            for persona_id, content in st.session_state.personas.items():
                segment_name = clean_text(next((s.get("name", "Unknown") for s in segments_for_chat if s.get("id", -1) == persona_id), "Unknown"))
                st.info(f"Cluster {persona_id}: {segment_name}")
        else:
            st.warning("Aucun persona genere. Generez d'abord des personas")
        
        st.divider()
        st.write("Posez des questions sur les personas, les segments ou demandez des recommandations marketing.")
        
        for message in st.session_state.conversation_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        user_input = st.chat_input("Posez votre question...")
        
        if user_input:
            st.session_state.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            with st.chat_message("user"):
                st.markdown(user_input)
            
            try:
                personas_context = "PERSONAS GENERES:\n"
                if st.session_state.personas:
                    for persona_id, content in st.session_state.personas.items():
                        segment_name = clean_text(next((s.get("name", "Unknown") for s in segments_for_chat if s.get("id", -1) == persona_id), "Unknown"))
                        clean_content = clean_text(content[:2000])
                        personas_context += f"\n--- Cluster {persona_id}: {segment_name} ---\n{clean_content}...\n"
                else:
                    personas_context += "Aucun persona genere."
                
                segments_context = "\n\nSEGMENTS:\n"
                for segment in segments_for_chat:
                    clean_seg = {k: clean_text(v) for k, v in segment.items()}
                    segments_context += f"- ID: {clean_seg.get('id')}, Nom: {clean_seg.get('name')}, Age: {clean_seg.get('age')}, "
                    segments_context += f"Produits: {clean_seg.get('nbProducts')}, Revenu H: {clean_seg.get('revenueHommes')}, Revenu F: {clean_seg.get('revenueFemmes')}\n"
                
                if st.session_state.produits_bancaires_text:
                    produits_context = f"\n\nCATALOGUE PRODUITS:\n{clean_text(st.session_state.produits_bancaires_text[:8000])}"
                else:
                    produits_context = "\n\nNote: Aucun catalogue produits charge."
                
                system_prompt = f"""Tu es un expert en marketing bancaire et segmentation client de Societe Generale Cote d'Ivoire.

{personas_context}
{segments_context}
{produits_context}

Utilise ces informations pour repondre aux questions. Recommande des produits specifiques avec tarifs quand le catalogue est disponible."""
                
                messages_with_system = [
                    {"role": "system", "content": system_prompt}
                ] + st.session_state.conversation_history
                
                response = st.session_state.client.chat.completions.create(
                    model=model_choice,
                    max_tokens=2000,
                    messages=messages_with_system
                )
                
                assistant_message = response.choices[0].message.content
                st.session_state.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })
                
                with st.chat_message("assistant"):
                    st.markdown(assistant_message)
            
            except Exception as e:
                st.error(f"Erreur: {str(e)}")
