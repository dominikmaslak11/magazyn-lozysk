package pl.lozyska.offline

import androidx.camera.core.CameraSelector
import androidx.camera.core.ExperimentalGetImage
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import java.util.concurrent.Executors

/**
 * Pełnoekranowy skaner kodów QR/kreskowych na etykietach i opakowaniach łożysk.
 * Rozpoznawanie działa w całości na urządzeniu (ML Kit on-device) - obraz z kamery
 * nigdy nie opuszcza telefonu. Zwraca surowy tekst kodu przy pierwszym udanym odczycie
 * i od razu zamyka podgląd (patrz `onResult`).
 */
/**
 * Czy zeskanowany kod to handlowy kod produktu (EAN/UPC) z opakowania?
 *
 * To rozróżnienie jest istotne: EAN-13 na pudełku łożyska koduje numer produktu w systemie
 * sprzedaży producenta, a NIE oznaczenie łożyska - nie da się z niego odczytać symbolu ani
 * wymiarów. Nasze własne naklejki QR (patrz pdf_labels.py) zawierają wprost symbol, więc te
 * można użyć od razu.
 */
fun isProductBarcodeFormat(format: Int): Boolean = format in setOf(
    Barcode.FORMAT_EAN_13, Barcode.FORMAT_EAN_8,
    Barcode.FORMAT_UPC_A, Barcode.FORMAT_UPC_E,
)

@OptIn(ExperimentalGetImage::class)
@Composable
fun BarcodeScannerScreen(onResult: (String, Boolean) -> Unit, onClose: () -> Unit) {
    Dialog(
        onDismissRequest = onClose,
        properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false),
    ) {
        val context = LocalContext.current
        val lifecycleOwner = LocalLifecycleOwner.current
        val previewView = remember { PreviewView(context) }
        var errorMessage by remember { mutableStateOf<String?>(null) }

        DisposableEffect(lifecycleOwner) {
            var hasResult = false
            val cameraExecutor = Executors.newSingleThreadExecutor()
            val scanner = BarcodeScanning.getClient(
                BarcodeScannerOptions.Builder().setBarcodeFormats(Barcode.FORMAT_ALL_FORMATS).build()
            )
            val cameraProviderFuture = ProcessCameraProvider.getInstance(context)
            cameraProviderFuture.addListener({
                val cameraProvider = cameraProviderFuture.get()
                val preview = Preview.Builder().build().also { it.setSurfaceProvider(previewView.surfaceProvider) }
                val analysis = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .build()
                analysis.setAnalyzer(cameraExecutor) { imageProxy ->
                    val mediaImage = imageProxy.image
                    if (mediaImage == null || hasResult) {
                        imageProxy.close()
                    } else {
                        val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
                        scanner.process(image)
                            .addOnSuccessListener { barcodes ->
                                val hit = barcodes.firstOrNull { !it.rawValue.isNullOrBlank() }
                                val value = hit?.rawValue
                                if (value != null && !hasResult) {
                                    hasResult = true
                                    onResult(value, isProductBarcodeFormat(hit.format))
                                }
                            }
                            .addOnCompleteListener { imageProxy.close() }
                    }
                }
                try {
                    cameraProvider.unbindAll()
                    cameraProvider.bindToLifecycle(lifecycleOwner, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
                } catch (e: Exception) {
                    errorMessage = "Nie udało się uruchomić aparatu: ${e.message}"
                }
            }, ContextCompat.getMainExecutor(context))

            onDispose {
                cameraExecutor.shutdown()
                scanner.close()
                runCatching { cameraProviderFuture.get().unbindAll() }
            }
        }

        Box(Modifier.fillMaxSize()) {
            AndroidView(factory = { previewView }, modifier = Modifier.fillMaxSize())

            Surface(color = Color.Black.copy(alpha = 0.6f), modifier = Modifier.fillMaxWidth().align(Alignment.TopCenter)) {
                Row(
                    Modifier.fillMaxWidth().padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("Skieruj aparat na kod QR / kreskowy", color = Color.White, style = MaterialTheme.typography.bodyMedium)
                    IconButton(onClick = onClose) { Icon(Icons.Filled.Close, contentDescription = "Zamknij", tint = Color.White) }
                }
            }

            errorMessage?.let {
                Surface(
                    color = MaterialTheme.colorScheme.errorContainer,
                    modifier = Modifier.align(Alignment.BottomCenter).fillMaxWidth().padding(16.dp),
                ) {
                    Text(it, color = MaterialTheme.colorScheme.onErrorContainer, modifier = Modifier.padding(12.dp))
                }
            }
        }
    }
}
