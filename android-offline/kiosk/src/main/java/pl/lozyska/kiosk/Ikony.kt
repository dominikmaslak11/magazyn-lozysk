package pl.lozyska.kiosk

import android.graphics.Canvas
import android.graphics.ColorFilter
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PixelFormat
import android.graphics.RectF
import android.graphics.drawable.Drawable

/**
 * Ikony rysowane w kodzie na Canvasie.
 *
 * Dlaczego nie znaki Unicode ani wektory: Android 4.2 nie ma VectorDrawable, a jego
 * czcionka nie ma wiekszosci symboli (zamiast ikony wyskakuje pusty prostokat).
 * Canvas dziala wszedzie i daje ostre linie w kazdym kolorze motywu.
 */
class Ikona(private val rodzaj: Rodzaj, private var kolor: Int, private val rozmiar: Int) : Drawable() {

    enum class Rodzaj { LUPA, ZEGAR, MOTYW, OBROT, ODSWIEZ, PLUS, MINUS, STRZALKA_GORA, STRZALKA_DOL, OSTRZEZENIE }

    private val pedzel = Paint(Paint.ANTI_ALIAS_FLAG)

    init {
        setBounds(0, 0, rozmiar, rozmiar)
    }

    fun ustawKolor(nowy: Int) {
        kolor = nowy
        invalidateSelf()
    }

    override fun getIntrinsicWidth() = rozmiar
    override fun getIntrinsicHeight() = rozmiar

    override fun draw(c: Canvas) {
        val r = rozmiar.toFloat()
        val grubosc = r / 10f
        pedzel.color = kolor
        pedzel.style = Paint.Style.STROKE
        pedzel.strokeWidth = grubosc
        pedzel.strokeCap = Paint.Cap.ROUND
        val p = grubosc * 1.5f                       // margines, zeby gruba linia nie wychodzila poza pole
        val pole = RectF(p, p, r - p, r - p)
        when (rodzaj) {
            Rodzaj.LUPA -> {
                c.drawCircle(r * 0.42f, r * 0.42f, r * 0.28f, pedzel)
                c.drawLine(r * 0.63f, r * 0.63f, r - p, r - p, pedzel)
            }
            Rodzaj.ZEGAR -> {
                c.drawCircle(r / 2, r / 2, r / 2 - p, pedzel)
                c.drawLine(r / 2, r / 2, r / 2, r * 0.22f, pedzel)
                c.drawLine(r / 2, r / 2, r * 0.7f, r * 0.6f, pedzel)
            }
            Rodzaj.MOTYW -> {
                c.drawCircle(r / 2, r / 2, r / 2 - p, pedzel)
                pedzel.style = Paint.Style.FILL
                c.drawArc(pole, 90f, 180f, true, pedzel)     // lewa polowa pelna: jasne/ciemne
            }
            Rodzaj.OBROT, Rodzaj.ODSWIEZ -> {
                val poczatek = if (rodzaj == Rodzaj.OBROT) 40f else 60f
                c.drawArc(pole, poczatek, 270f, false, pedzel)
                // grot na koncu luku
                val kat = Math.toRadians((poczatek + 270f).toDouble())
                val cx = r / 2 + (r / 2 - p) * Math.cos(kat).toFloat()
                val cy = r / 2 + (r / 2 - p) * Math.sin(kat).toFloat()
                pedzel.style = Paint.Style.FILL
                val grot = Path()
                val d = r * 0.2f
                grot.moveTo(cx - d, cy - d * 0.2f)
                grot.lineTo(cx + d, cy - d * 0.2f)
                grot.lineTo(cx, cy + d * 1.2f)
                grot.close()
                c.drawPath(grot, pedzel)
                if (rodzaj == Rodzaj.OBROT) {
                    // mala ramka w srodku - "ekran", ktory sie obraca
                    pedzel.style = Paint.Style.STROKE
                    c.drawRect(r * 0.36f, r * 0.3f, r * 0.64f, r * 0.7f, pedzel)
                }
            }
            Rodzaj.PLUS -> {
                pedzel.strokeWidth = grubosc * 1.6f
                c.drawLine(r * 0.2f, r / 2, r * 0.8f, r / 2, pedzel)
                c.drawLine(r / 2, r * 0.2f, r / 2, r * 0.8f, pedzel)
            }
            Rodzaj.MINUS -> {
                pedzel.strokeWidth = grubosc * 1.6f
                c.drawLine(r * 0.2f, r / 2, r * 0.8f, r / 2, pedzel)
            }
            Rodzaj.STRZALKA_GORA, Rodzaj.STRZALKA_DOL -> {
                pedzel.style = Paint.Style.FILL
                val t = Path()
                if (rodzaj == Rodzaj.STRZALKA_GORA) {
                    t.moveTo(r / 2, r * 0.15f); t.lineTo(r * 0.9f, r * 0.85f); t.lineTo(r * 0.1f, r * 0.85f)
                } else {
                    t.moveTo(r / 2, r * 0.85f); t.lineTo(r * 0.9f, r * 0.15f); t.lineTo(r * 0.1f, r * 0.15f)
                }
                t.close()
                c.drawPath(t, pedzel)
            }
            Rodzaj.OSTRZEZENIE -> {
                val t = Path()
                t.moveTo(r / 2, p); t.lineTo(r - p, r - p); t.lineTo(p, r - p); t.close()
                c.drawPath(t, pedzel)
                c.drawLine(r / 2, r * 0.38f, r / 2, r * 0.64f, pedzel)
                pedzel.style = Paint.Style.FILL
                c.drawCircle(r / 2, r * 0.78f, grubosc * 0.7f, pedzel)
            }
        }
    }

    override fun setAlpha(alpha: Int) {}
    override fun setColorFilter(filtr: ColorFilter?) {}
    override fun getOpacity() = PixelFormat.TRANSLUCENT
}
