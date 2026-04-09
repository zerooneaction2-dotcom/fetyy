package com.example.certificate

import android.os.Bundle
import android.print.PrintAttributes
import android.print.PrintManager
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity
import android.widget.Button

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webview)
        val btnPrint: Button = findViewById(R.id.btnPrint)

        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.webViewClient = WebViewClient()

        // Load the local certificate HTML from assets
        webView.loadUrl("file:///android_asset/index.html")

        btnPrint.setOnClickListener {
            createWebPrintJob(webView)
        }
    }

    private fun createWebPrintJob(webView: WebView) {
        val printManager = getSystemService(PRINT_SERVICE) as PrintManager
        val jobName = "Certificate_Print_Job"

        val printAdapter = webView.createPrintDocumentAdapter(jobName)
        val builder = PrintAttributes.Builder()
        builder.setMediaSize(PrintAttributes.MediaSize.ISO_A4)
        builder.setColorMode(PrintAttributes.COLOR_MODE_COLOR)

        printManager.print(jobName, printAdapter, builder.build())
    }
}
