export const downloadFile = async (url: string, title: string) => {
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = url;
    a.download = title;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };