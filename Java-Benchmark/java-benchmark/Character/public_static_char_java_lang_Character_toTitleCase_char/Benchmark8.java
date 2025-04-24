

public class Benchmark8 {
    public static void main(String[] args) {
        // fetch input
        Character input_1_0 = args[0].charAt(0);
        Character input_2_0 = args[1].charAt(0);


        // Perform computation         
        Character output_1 = Character.toTitleCase(input_1_0);
        Character output_2 = Character.toTitleCase(input_2_0);

        
        // Compare output
        if (output_1 == ',' && output_2 == '-') {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

