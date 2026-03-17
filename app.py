# --- LENDER COMPARISON SECTION ---
st.subheader("Lender Eligibility & Detailed Source Audit")

for r in results:
    is_eligible = "✅" in r['status']
    with st.expander(f"{r['status']} | {r['bank']}", expanded=True):
        
        tab_main, tab_audit = st.tabs(["Analysis", "🔍 Structural Source Audit"])
        
        with tab_main:
            if not is_eligible:
                for msg in r['reasons']: st.error(msg)
            else:
                st.success(f"Qualified via {r['bank']}")
                st.write(f"**Monthly PITIA:** ${r['pitia']:,.2f}")

        with tab_audit:
            st.caption("The engine extracted these specific rules from your uploaded documents:")
            
            # Display citations in a structured table
            for entry in r['audit']:
                st.markdown(f"""
                ---
                **📄 Document:** `{entry['doc']}`  
                **🏷️ Program:** {entry['program']}  
                **📍 Location:** {entry['location']}  
                **📝 Rule Context:** {entry['context']}
                """)