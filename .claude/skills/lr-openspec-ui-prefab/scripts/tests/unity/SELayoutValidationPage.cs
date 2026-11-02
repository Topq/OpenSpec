using UnityEngine;
using UnityEngine.UI;
using TMPro;

namespace SEOpenSpecValidation
{
    // Deployed temporarily outside Editor, so references survive prefab reload.
    public class SELayoutValidationPage : MonoBehaviour
    {
        [SerializeField] [Header("Close")]
        private Button closeButton;
        [SerializeField, HideInInspector] private Button[] m_Buttons;
        [SerializeField] private TMP_Text m_Title;
        [SerializeField] private GameObject m_TitleObject;
        [SerializeField] private SELayoutValidationCell m_First;
        [SerializeField] private SELayoutValidationCell m_Second;
    }
}
