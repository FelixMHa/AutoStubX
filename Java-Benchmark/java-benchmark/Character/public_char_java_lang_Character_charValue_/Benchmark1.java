

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Character input_1_0 = args[0].charAt(0);
        Character input_2_0 = args[1].charAt(0);


        // Perform computation         
        Character output_1 = input_1_0.charValue();
        Character output_2 = input_2_0.charValue();

        
        // Compare output
        if (output_1 == ':' && output_2 == 'z') {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

