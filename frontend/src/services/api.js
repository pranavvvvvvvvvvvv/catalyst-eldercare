import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

export const speakText = (text, locale = "mr-IN") => {
  if ("speechSynthesis" in window && text) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = locale;
    utterance.rate = 0.92;
    window.speechSynthesis.speak(utterance);
  }
};

export const UI_TRANSLATIONS = {
  en: {
    title: "Catalyst ElderCare",
    sosBtn: "EMERGENCY SOS (Hold or Say 'Ambulance')",
    cancelSos: "CANCEL AMBULANCE CALL",
    generatingPin: "Generate 15-Min Doctor Access PIN",
    ongoingMeds: "Ongoing Medication Courses",
    firstAidTitle: "Doctor-Prescribed Emergency First Aid",
    readAloud: "Read Aloud",
    beforeMeal: "Before Meal",
    afterMeal: "After Meal",
  },
  hi: {
    title: "कैटेलिस्ट बुजुर्ग स्वास्थ्य सेवा",
    sosBtn: "आपातकालीन SOS ('एम्बुलेंस' बोलें)",
    cancelSos: "एम्बुलेंस कॉल रद्द करें",
    generatingPin: "डॉक्टर के लिए 15-मिनट का पिन बनाएं",
    ongoingMeds: "चल रही दवाइयों का कोर्स",
    firstAidTitle: "डॉक्टर द्वारा सुझाया गया प्राथमिक उपचार",
    readAloud: "आवाज़ में सुनें",
    beforeMeal: "खाने से पहले",
    afterMeal: "खाने के बाद",
  },
  mr: {
    title: "कॅटॅलिस्ट ज्येष्ठ नागरिक आरोग्य सेवा",
    sosBtn: "आपत्कालीन SOS ('ॲम्ब्युलन्स' म्हणा)",
    cancelSos: "ॲम्ब्युलन्स कॉल रद्द करा",
    generatingPin: "डॉक्टरांसाठी १५-मिनिटांचा पिन तयार करा",
    ongoingMeds: "सुरू असलेले औषधांचे कोर्स",
    firstAidTitle: "डॉक्टरांनी दिलेले आपत्कालीन प्रथमोपचार",
    readAloud: "आवाजात ऐका",
    beforeMeal: "जेवणापूर्वी",
    afterMeal: "जेवणानंतर",
  },
};