import streamlit as st
import pandas as pd
import json
from openai import OpenAI
import PyPDF2
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Configuration Streamlit
st.set_page_config(
    page_title="Générateur de Personas Marketing",
    page_icon="🎯",
    layout="wide"
)

# CSS personnalisé
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
        <h1>🎯 Générateur de Personas Marketing</h1>
        <p>Générez automatiquement des descriptions de personas pour chaque segment client</p>
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
    st.header("⚙️ Configuration")
    
    # API Key
    api_key = st.text_input("Clé API OpenAI", type="password", key="api_key")
    
    if api_key and st.session_state.client is None:
        st.session_state.client = OpenAI(api_key=api_key)
        st.success("✅ Connecté à OpenAI !")
    
    st.divider()
    
    # Section Upload PDF
    st.header("📄 Catalogue Produits")
    
    uploaded_pdf = st.file_uploader(
        "Charger le PDF des conditions bancaires",
        type=["pdf"],
        help="Uploadez le document des conditions générales de la banque (mis à jour chaque semestre)"
    )
    
    if uploaded_pdf is not None:
        try:
            # Lire le PDF
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_pdf.read()))
            
            # Extraire le texte
            pdf_text = ""
            for page in pdf_reader.pages:
                pdf_text += page.extract_text() + "\n"
            
            st.session_state.produits_bancaires_text = pdf_text
            
            st.success(f"✅ PDF chargé ! ({len(pdf_reader.pages)} pages)")
            
            # Aperçu
            with st.expander("📄 Aperçu du contenu"):
                st.text(pdf_text[:800] + "...")
                
        except Exception as e:
            st.error(f"❌ Erreur lors de la lecture du PDF: {e}")
    
    elif st.session_state.produits_bancaires_text:
        st.info("✅ Catalogue produits chargé en mémoire")
        if st.button("🗑️ Supprimer le catalogue"):
            st.session_state.produits_bancaires_text = None
            st.rerun()
    else:
        st.warning("⚠️ Aucun catalogue chargé")
        st.caption("Les personas seront générés sans recommandations de produits spécifiques")
    
    st.divider()
    
    # Options
    st.header("📊 Options")
    
    model_choice = st.selectbox(
        "Modèle OpenAI",
        ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        index=0
    )
    
    st.divider()
    st.info("💡 Configurez votre clé API OpenAI et chargez le catalogue produits pour commencer")

# Données des segments par défaut
segments_data = [
    {
        "id": 0,
        "name": "Les clients fidèles et hyper-connectés",
        "age": 40,
        "nbProducts": 8,
        "revenueHommes": "100 000 - 200 000 FCFA",
        "revenueFemmes": "100 000 - 200 000 FCFA",
        "mobileAccess": "99%",
        "emailAccess": "85%",
        "characteristics": "Maturité professionnelle, clients de base stable"
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
        "characteristics": "En transition professionnelle, hyper-connectés"
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
        "name": "Les fidèles discrets",
        "age": 41,
        "nbProducts": 3,
        "revenueHommes": "0 - 100 000 FCFA",
        "revenueFemmes": "0 - 100 000 FCFA",
        "mobileAccess": "98%",
        "emailAccess": "N/A",
        "characteristics": "Employés stables, utilisation minimale"
    }
]

def create_prompt(segment):
    base_info = f"""Génère une description complète et détaillée d'une persona marketing pour un segment bancaire avec les caractéristiques suivantes:

Nom du segment: {segment.get('name', 'N/A')}
Âge moyen: {segment.get('age', 'N/A')} ans
Nombre de produits utilisés: {segment.get('nbProducts', 'N/A')}
Revenu mensuel (Hommes): {segment.get('revenueHommes', 'N/A')}
Revenu mensuel (Femmes): {segment.get('revenueFemmes', 'N/A')}
Accessibilité mobile: {segment.get('mobileAccess', 'N/A')}
Accessibilité email: {segment.get('emailAccess', 'N/A')}
Caractéristiques principales: {segment.get('characteristics', 'N/A')}"""

    if st.session_state.produits_bancaires_text:
        produits_info = f"""

CATALOGUE DES PRODUITS BANCAIRES DISPONIBLES:
{st.session_state.produits_bancaires_text[:8000]}

IMPORTANT: Utilise ce catalogue pour recommander des produits SPÉCIFIQUES avec leurs TARIFS EXACTS du catalogue."""
    else:
        produits_info = "\n\nNote: Aucun catalogue produits chargé. Fais des recommandations générales sans tarifs spécifiques."
    
    prompt = base_info + produits_info + """

Fournis une description professionnelle en français incluant:
- Profil démographique détaillé (avec différences possibles entre hommes et femmes)
- Comportements d'achat et patterns de consommation
- Besoins et préférences spécifiques
- Motivations et douleurs (pain points)
- Stratégie marketing recommandée
- Canaux de communication préférés
- Proposition de valeur unique
- RECOMMANDATIONS DE PRODUITS BANCAIRES ADAPTÉS avec les tarifs exacts du catalogue (si disponible)
- Crée un package produit en enumerant les elements de ce package en , si possible

Format: Utilise des sections claires avec des titres en gras."""
    
    return prompt

def generate_persona_pdf(persona_id, persona_content, segment_name):
    """
    Génère un PDF formaté pour un persona
    """
    buffer = io.BytesIO()
    
    # Créer le document PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#d32f2f',
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Style pour les sous-titres
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor='#b71c1c',
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Style pour le texte normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_JUSTIFY,
        spaceAfter=10
    )
    
    # Contenu du PDF
    story = []
    
    # Titre
    story.append(Paragraph(f"PERSONA MARKETING", title_style))
    story.append(Paragraph(f"Cluster {persona_id}: {segment_name}", heading_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Convertir le contenu markdown en paragraphes PDF
    lines = persona_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.3*cm))
            continue
        
        # Détection des titres (lignes avec **)
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
        elif line.startswith('- ') or line.startswith('• '):
            # Liste à puces
            text = line[2:].strip()
            story.append(Paragraph(f"• {text}", normal_style))
        else:
            # Texte normal - nettoyer le markdown basique
            text = line.replace('**', '')
            if text:
                story.append(Paragraph(text, normal_style))
    
    # Footer
    story.append(Spacer(1, 1*cm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor='gray',
        alignment=TA_CENTER
    )
    story.append(Paragraph("Généré par le Générateur de Personas Marketing - Société Générale Côte d'Ivoire", footer_style))
    
    # Générer le PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer

def generate_persona(segment, model):
    """
    Génère un persona avec OpenAI
    """
    if st.session_state.client is None:
        st.error("❌ Veuillez d'abord configurer votre clé API OpenAI dans la barre latérale.")
        return None
    
    prompt = create_prompt(segment)
    
    try:
        message = st.session_state.client.chat.completions.create(
            model=model,
            max_tokens=2500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        st.session_state.personas[segment.get("id", 0)] = message.choices[0].message.content
        return message.choices[0].message.content
    
    except Exception as e:
        st.error(f"❌ Erreur lors de la génération: {e}")
        return None
    if st.session_state.client is None:
        st.error("❌ Veuillez d'abord configurer votre clé API OpenAI dans la barre latérale.")
        return None
    
    prompt = create_prompt(segment)
    
    try:
        message = st.session_state.client.chat.completions.create(
            model=model,
            max_tokens=2500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        st.session_state.personas[segment.get("id", 0)] = message.choices[0].message.content
        return message.choices[0].message.content
    
    except Exception as e:
        st.error(f"❌ Erreur lors de la génération: {e}")
        return None

# Onglets principaux
tab1, tab2, tab3 = st.tabs(["📋 Segments", "🎯 Générer Personas", "💬 Chat Intelligent"])

# TAB 1 - SEGMENTS
with tab1:
    st.subheader("Segments Clients Disponibles")
    
    data_source = st.radio(
        "Source de données",
        ["Données par défaut", "Charger un CSV personnalisé"],
        index=0
    )
    
    if data_source == "Charger un CSV personnalisé":
        st.divider()
        st.subheader("📤 Charger vos propres données")
        uploaded_file = st.file_uploader("Chargez un fichier CSV avec vos segments", type="csv")
        
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.session_state.loaded_segments = df.to_dict('records')
            st.dataframe(df, use_container_width=True)
            st.success("✅ Fichier chargé avec succès!")
            current_segments = st.session_state.loaded_segments
        else:
            st.info("💡 Veuillez charger un fichier CSV pour continuer")
            current_segments = []
    else:
        current_segments = segments_data
    
    if current_segments:
        st.divider()
        st.subheader("Segments à traiter")
        cols = st.columns(2)
        for idx, segment in enumerate(current_segments):
            with cols[idx % 2]:
                st.markdown(f"""
                <div class="cluster-box">
                    <h4>CLUSTER {segment.get('id', idx)}: {segment.get('name', 'Sans nom')}</h4>
                    <p><b>Âge moyen:</b> {segment.get('age', 'N/A')} ans</p>
                    <p><b>Produits:</b> {segment.get('nbProducts', 'N/A')}</p>
                    <p><b>Revenu Hommes:</b> {segment.get('revenueHommes', 'N/A')}</p>
                    <p><b>Revenu Femmes:</b> {segment.get('revenueFemmes', 'N/A')}</p>
                    <p><b>Accès Mobile:</b> {segment.get('mobileAccess', 'N/A')}</p>
                    <p><b>Accès Email:</b> {segment.get('emailAccess', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)

# TAB 2 - GÉNÉRATION
with tab2:
    st.subheader("🎯 Générer des Personas")
    
    if "loaded_segments" in st.session_state and st.session_state.loaded_segments:
        segments_to_use = st.session_state.loaded_segments
    else:
        segments_to_use = segments_data
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.write("**Segments disponibles:**")
        selected_segments = st.multiselect(
            "Sélectionnez les segments à traiter",
            options=[(s.get("id", idx), s.get("name", f"Segment {idx}")) for idx, s in enumerate(segments_to_use)],
            format_func=lambda x: f"Cluster {x[0]}: {x[1][:30]}...",
            default=[(segments_to_use[0].get("id", 0), segments_to_use[0].get("name", "Segment 0"))]
        )
        
        if st.button("🚀 Générer les Personas", type="primary"):
            if not selected_segments:
                st.warning("⚠️ Sélectionnez au moins un segment")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, (seg_id, _) in enumerate(selected_segments):
                    segment = next((s for s in segments_to_use if s.get("id", -1) == seg_id), None)
                    if segment:
                        status_text.text(f"Génération du Cluster {seg_id}...")
                        
                        generate_persona(segment, model_choice)
                        
                        progress_bar.progress((idx + 1) / len(selected_segments))
                
                st.success("✅ Tous les personas ont été générés!")
    
    with col2:
        if st.session_state.personas:
            st.write("**Personas générés:**")
            
            persona_options = [
                f"Cluster {k}: {next((s.get('name', 'Unknown') for s in segments_to_use if s.get('id', -1) == k), 'Unknown')[:40]}..."
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
                        label="📥 Télécharger en TXT",
                        data=st.session_state.personas[persona_id],
                        file_name=f"persona_cluster_{persona_id}.txt",
                        mime="text/plain"
                    )
                
                with col_b:
                    segment_name = next((s.get("name", "Unknown") for s in segments_to_use if s.get("id", -1) == persona_id), "Unknown")
                    
                    # Générer le PDF
                    pdf_buffer = generate_persona_pdf(persona_id, st.session_state.personas[persona_id], segment_name)
                    
                    st.download_button(
                        label="📥 Télécharger en PDF",
                        data=pdf_buffer,
                        file_name=f"persona_cluster_{persona_id}.pdf",
                        mime="application/pdf"
                    )
        else:
            st.info("💡 Générez des personas pour les voir ici")

# TAB 3 - CHAT
with tab3:
    st.subheader("💬 Assistant Intelligent pour Personas")
    
    if st.session_state.client is None:
        st.warning("⚠️ Veuillez configurer votre clé API OpenAI d'abord.")
    else:
        if "loaded_segments" in st.session_state and st.session_state.loaded_segments:
            segments_for_chat = st.session_state.loaded_segments
        else:
            segments_for_chat = segments_data
        
        st.write("**Personas générés disponibles:**")
        if st.session_state.personas:
            for persona_id, content in st.session_state.personas.items():
                segment_name = next((s.get("name", "Unknown") for s in segments_for_chat if s.get("id", -1) == persona_id), "Unknown")
                st.info(f"✅ Cluster {persona_id}: {segment_name}")
        else:
            st.warning("⚠️ Aucun persona généré. Générez d'abord des personas dans l'onglet 'Générer Personas'")
        
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
                personas_context = "PERSONAS GÉNÉRÉS:\n"
                if st.session_state.personas:
                    for persona_id, content in st.session_state.personas.items():
                        segment_name = next((s.get("name", "Unknown") for s in segments_for_chat if s.get("id", -1) == persona_id), "Unknown")
                        personas_context += f"\n--- Cluster {persona_id}: {segment_name} ---\n{content[:2000]}...\n"
                else:
                    personas_context += "Aucun persona généré."
                
                segments_context = "\n\nSEGMENTS:\n"
                for segment in segments_for_chat:
                    segments_context += f"- ID: {segment.get('id')}, Nom: {segment.get('name')}, Âge: {segment.get('age')}, "
                    segments_context += f"Produits: {segment.get('nbProducts')}, Revenu H: {segment.get('revenueHommes')}, Revenu F: {segment.get('revenueFemmes')}\n"
                
                if st.session_state.produits_bancaires_text:
                    produits_context = f"\n\nCATALOGUE PRODUITS:\n{st.session_state.produits_bancaires_text[:8000]}"
                else:
                    produits_context = "\n\nNote: Aucun catalogue produits chargé."
                
                system_prompt = f"""Tu es un expert en marketing bancaire et segmentation client de Société Générale Côte d'Ivoire.

{personas_context}
{segments_context}
{produits_context}

Utilise ces informations pour répondre aux questions. Recommande des produits spécifiques avec tarifs quand le catalogue est disponible."""
                
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
                st.error(f"❌ Erreur: {e}")