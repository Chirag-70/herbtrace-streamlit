'''import streamlit as st

CNN_CLASSIFIER_URL = "https://brqhdhhv5diwqbg9jixjfc.streamlit.app/"


def show_herb_classifier(herb_name):
    st.subheader("🤖 CNN Herb Identification")

    st.info(
        "Use the CNN Herb Identifier below to verify whether the captured herb "
        "matches the herb name entered above."
    )

    st.write(f"Farmer-entered herb name: **{herb_name}**")

    st.link_button(
        "🌿 Open CNN Herb Identifier",
        CNN_CLASSIFIER_URL,
        use_container_width=True,
    )

    with st.expander("Open CNN classifier inside HerbTrace"):
        st.components.v1.iframe(
            CNN_CLASSIFIER_URL,
            height=700,
            scrolling=True,
        )

    st.warning(
        "Compare the CNN prediction with the farmer-entered herb name before "
        "creating the collection batch."
    )'''
