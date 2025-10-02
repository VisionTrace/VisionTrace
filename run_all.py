from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
import subprocess


class MainLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=10, padding=20, **kwargs)

        self.add_widget(Label(text="Enter Instagram Username:", font_size=20))

        self.username_input = TextInput(multiline=False, font_size=18, size_hint_y=None, height=40)
        self.add_widget(self.username_input)

        self.run_button = Button(text="Run Pipeline", size_hint_y=None, height=50)
        self.run_button.bind(on_press=self.run_pipeline)
        self.add_widget(self.run_button)

        self.output_label = Label(text="", font_size=16)
        self.add_widget(self.output_label)

    def run_pipeline(self, instance):
        username = self.username_input.text.strip()
        if not username:
            self.output_label.text = "⚠️ Please enter a username."
            return

        files = [
            ["python", "scrape.py", username],
            ["python", "analyze.py"],
            ["python", "predict2.py"],
        ]

        try:
            for f in files:
                self.output_label.text = f"Running {f[1]}..."
                subprocess.run(f)
            self.output_label.text = "✅ All files finished successfully!"
        except Exception as e:
            self.output_label.text = f"❌ Error: {e}"


class MyApp(App):
    def build(self):
        return MainLayout()


if __name__ == "__main__":
    MyApp().run()
